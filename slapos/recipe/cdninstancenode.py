import dns.resolver
import hmac
import hashlib
import ipaddress
import time
import os
try:
  from secrets import token_hex
except ImportError:
  from os import urandom
  token_hex = lambda n: urandom(n).hex()
from six.moves.urllib.parse import urlsplit, urlparse
import re
import subprocess
import json
import sys
import logging
from slapos.recipe.instancenode import (
  Recipe as InstanceNodeRecipe,
  parse_command_line_args,
  load_config_and_create_objects,
  configure_logging
)
from slapos.recipe.localinstancedb import LocalDBAccessor
from zc.buildout import UserError

# Cipher constants from instance-master.cfg.in
GOOD_CIPHER_LIST = [
  'ECDHE-ECDSA-AES256-GCM-SHA384',
  'ECDHE-RSA-AES256-GCM-SHA384',
  'ECDHE-ECDSA-AES128-GCM-SHA256',
  'ECDHE-RSA-AES128-GCM-SHA256',
  'ECDHE-ECDSA-CHACHA20-POLY1305',
  'ECDHE-RSA-CHACHA20-POLY1305',
  'ECDHE-RSA-AES256-SHA',
  'ECDHE-RSA-AES128-SHA',
  'ECDHE-ECDSA-AES256-SHA',
  'ECDHE-ECDSA-AES128-SHA',
  'AES256-SHA',
  'AES128-SHA',
  'ECDHE-RSA-DES-CBC3-SHA',
  'DES-CBC3-SHA'
]

CIPHER_TRANSLATION_DICT = {
  'ECDHE-ECDSA-WITH-CHACHA20-POLY1305': 'ECDHE-ECDSA-CHACHA20-POLY1305',
  'ECDHE-RSA-WITH-CHACHA20-POLY1305': 'ECDHE-RSA-CHACHA20-POLY1305',
  'ECDHE-RSA-AES256-CBC-SHA': 'ECDHE-RSA-AES256-SHA',
  'ECDHE-RSA-AES128-CBC-SHA': 'ECDHE-RSA-AES128-SHA',
  'ECDHE-ECDSA-AES256-CBC-SHA': 'ECDHE-ECDSA-AES256-SHA',
  'ECDHE-ECDSA-AES128-CBC-SHA': 'ECDHE-ECDSA-AES128-SHA',
  'RSA-AES256-CBC-SHA': 'AES256-SHA',
  'RSA-AES128-CBC-SHA': 'AES128-SHA',
  'ECDHE-RSA-3DES-EDE-CBC-SHA': 'ECDHE-RSA-DES-CBC3-SHA',
  'RSA-3DES-EDE-CBC-SHA': 'DES-CBC3-SHA'
}

class DomainValidationDB(LocalDBAccessor):
  schema = """CREATE TABLE IF NOT EXISTS domain_validation (
    instance_reference VARCHAR(255) unique,
    domain VARCHAR(255),
    token VARCHAR(255),
    validated BOOLEAN,
    timestamp VARCHAR(255),
    PRIMARY KEY (instance_reference)
    );
    CREATE INDEX IF NOT EXISTS idx_instance_reference ON domain_validation(instance_reference);
    CREATE TABLE IF NOT EXISTS used_hosts (
      host VARCHAR(255),
      instance_reference VARCHAR(255),
      PRIMARY KEY (host, instance_reference)
    );
    CREATE INDEX IF NOT EXISTS idx_host ON used_hosts(host);
    CREATE INDEX IF NOT EXISTS idx_instance_reference_hosts ON used_hosts(instance_reference);"""

  def __init__(self, db_path):
    super(DomainValidationDB, self).__init__(db_path, self.schema)

  def getDomainValidationForInstance(self, instance_reference):
    """
    Get domain validation entry for a given instance reference.
    Returns row.
    """
    return self.fetchOne(
      "SELECT * FROM domain_validation WHERE instance_reference=?",
      (instance_reference,)
    )

  def getValidatedDomainForOtherInstance(self, domain, current_instance_reference):
    """
    Check if a domain is already validated for another instance.
    Returns the validation entry if found, None otherwise.
    """
    row = self.fetchOne(
      "SELECT * FROM domain_validation WHERE domain=? AND instance_reference!=? AND validated=?",
      (domain, current_instance_reference, True)
    )
    return row

  def removeDomainValidationForInstance(self, instance_reference):
    """
    Remove domain validation entry for an instance.
    Also removes all hosts for this instance from used_hosts table.
    """
    self.execute(
      "DELETE FROM domain_validation WHERE instance_reference=?",
      (instance_reference,)
    )
    self.execute(
      "DELETE FROM used_hosts WHERE instance_reference=?",
      (instance_reference,)
    )

  def addUsedHosts(self, instance_reference, hosts):
    """
    Add hosts for an instance to the used_hosts table.

    Args:
      instance_reference: Instance reference
      hosts: Set or list of host names (domains and aliases)
    """
    if not hosts:
      return
    # Replace any prior rows for this instance so stale aliases disappear.
    self.execute(
      "DELETE FROM used_hosts WHERE instance_reference=?",
      (instance_reference,)
    )
    host_list = [(host, instance_reference) for host in hosts]
    self.insertMany(
      "INSERT INTO used_hosts (host, instance_reference) VALUES (?, ?)",
      host_list
    )

  def isHostUsedByOtherInstance(self, host, current_instance_reference):
    """
    Check if a host is already used by another validated instance.
    Uses indexed lookup for O(log n) performance.

    Args:
      host: Host name to check
      current_instance_reference: Instance reference to exclude from check

    Returns:
      True if host is used by another instance, False otherwise
    """
    row = self.fetchOne(
      "SELECT instance_reference FROM used_hosts WHERE host=? AND instance_reference!=?",
      (host, current_instance_reference)
    )
    return row is not None

  def setDomainValidation(self, instance_reference, domain, token, validated):
    timestamp = str(int(time.time()))
    self.execute(
      "INSERT OR REPLACE INTO domain_validation VALUES (?, ?, ?, ?, ?)",
      (instance_reference, domain, token, validated, timestamp)
    )

class Recipe(InstanceNodeRecipe):
  """
  RequestInstanceListRecipe with custom domain verification for CDN.
  """

  def __init__(self, buildout, name, options):
    super(Recipe, self).__init__(buildout, name, options)
    self.instance_retention_delay = int(options.get('instance-retention-delay', '7776000'))
    self._already_retained_references = set()
    self.dns_entry_name = options.get('dns-entry-name', '_slapos-challenge')
    self.domain_validation_db = DomainValidationDB(self.options['domain-validation-db-path'])
    self.openssl_binary = options.get('openssl-binary')
    if not self.openssl_binary:
      self.logger.warning('openssl-binary option not provided, SSL certificate validation will be skipped')

    # Timestamp used to detect new DB writes since last run (bang gating).
    self.timestamp_path = options.get('timestamp-path')
    if self.timestamp_path and os.path.exists(self.timestamp_path):
      self.timestamp = os.path.getmtime(self.timestamp_path)
    else:
      self.timestamp = time.time()

    # Each comma-separated dns-nameserver entry may carry an explicit port
    # using `ip:port` (or `[ipv6]:port`); the default port is 53.
    dns_nameserver = options.get('dns-nameserver')

    # Fresh LRUCache so we bypass dnspython's global cache when querying
    # custom nameservers.
    self.dns_resolver = dns.resolver.Resolver()
    self.dns_resolver.lifetime = 5.0
    self.dns_resolver.cache = dns.resolver.LRUCache()

    if dns_nameserver:
      nameserver_ips = []
      nameserver_ports = {}
      for entry in dns_nameserver.split(','):
        entry = entry.strip()
        # Bare IPv6 (e.g. `2001:4860:4860::8888`) confuses urlsplit because
        # `:` is interpreted as port separator. Try parsing the entry as a
        # plain IP first; only fall back to ip:port parsing if it isn't one.
        try:
          ipaddress.ip_address(entry)
          nameserver_ips.append(entry)
          continue
        except ValueError:
          pass
        parsed = urlsplit('dns://' + entry)
        if parsed.hostname is None:
          raise UserError(
            'Invalid dns-nameserver entry: %r' % (entry,))
        nameserver_ips.append(parsed.hostname)
        if parsed.port:
          nameserver_ports[parsed.hostname] = parsed.port
      self.dns_nameservers = nameserver_ips
      # nameserver_ports must be assigned before nameservers: the setter
      # calls _enrich_nameservers(... self.nameserver_ports, self.port).
      self.dns_resolver.nameserver_ports = nameserver_ports
      self.dns_resolver.nameservers = nameserver_ips
      self.logger.info('Using custom nameserver(s) for DNS validation: %s', dns_nameserver)
    else:
      self.dns_nameservers = None

    # Path to the master's rendered instance-publish-slave-information.cfg.
    # When set, postDeployInstanceValidation rejects deployments whose
    # [publish-<reference>] section is absent from the file and signals
    # that a bang() is needed so the master rebuilds until it consumes
    # the frontend's now-published slave-instance-information-list.
    # Optional: when unset (or empty), the check is skipped (opt-in).
    self.publish_slave_information_file = options.get(
      'publish-slave-information-file') or None

  def _check_slave_publish_state(self, instance_reference):
    """
    Check that the master's instance-publish-slave-information.cfg
    already contains a ``[publish-<instance_reference>]`` section.

    The file is rendered on the master partition by the
    ``instance-publish-slave-information`` jinja2 template, which sources
    each section from the frontend's
    ``connection-slave-instance-information-list``. After a slave is added
    to a converged cluster, the master rebuilds once with stale frontend
    connection params (no section), then never re-rebuilds — leaving the
    section permanently absent. This helper detects that gap.

    Returns ``(is_valid, error_message, validation_info)`` following the
    same shape as ``_verifyCustomDomainDNS``.
    """
    if not self.publish_slave_information_file:
      return True, None, {}
    try:
      with open(self.publish_slave_information_file) as fh:
        content = fh.read()
    except IOError:
      content = None
    section = '[publish-%s]' % instance_reference
    if content is not None and section in content:
      return True, None, {}
    message = (
      'Cluster deployment in progress: slave publish entry not yet '
      'rendered in master publish file')
    return False, message, {'message': message}

  def _check_custom_domain(self, domain, token):
    """
    Check if the custom domain has the required TXT record.

    Uses a resolver with a fresh cache created at class initialization to bypass
    system DNS cache and remote DNS cache. This is important because:
    - Domain validation needs to detect new TXT records quickly
    - If validation runs every minute, we want to see DNS changes within ~1 minute
    - Default DNS TTL can be 300+ seconds, which would delay validation detection

    Cache behavior:
    - Resolver is created once at class initialization with a fresh cache.
    - This bypasses system DNS cache and remote DNS cache when using custom nameservers.
    - Each class initialization gets a fresh cache, ensuring different runs don't
      share cached DNS results.

    Nameserver behavior:
    - If dns-nameserver is provided: Queries directly to the specified nameserver(s)
      instead of using system DNS resolver. This bypasses local DNS cache and
      ensures consistent resolution.
    - If not provided: Uses system DNS resolver (default behavior)
    """
    challenge_domain = '%s.%s' % (self.dns_entry_name, domain)
    try:
      answers = self.dns_resolver.resolve(challenge_domain, 'TXT')

      for rdata in answers:
        # TXT records can be split across multiple strings
        txt_value = ''.join([x.decode('utf-8') for x in rdata.strings])
        if txt_value == token:
          return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout, dns.resolver.LifetimeTimeout):
      pass
    except Exception as e:
      self.logger.warning('DNS check failed for %s: %s', challenge_domain, e)
    return False

  def _getOrGenerateToken(self, instance_reference, custom_domain, validation_entry=None):
    """
    Get existing token or generate a new non-deterministic token for domain validation.

    If a validation_entry exists for the same domain, reuse its token.
    Otherwise, generate a new token using HMAC-SHA256 with instance_reference,
    custom_domain, and a random element.
    """
    if validation_entry and validation_entry['domain'] == custom_domain:
      # Reuse existing token (validation may still be incomplete)
      return validation_entry['token']

    random_component = token_hex(16)  # 32 hex characters
    secret = self.options.get('verification-secret', 'slapos-cdn-secret')
    message = '%s:%s:%s' % (instance_reference, custom_domain, random_component)
    key = secret.encode('utf-8')

    token = hmac.new(
      key,
      message.encode('utf-8'),
      hashlib.sha256
    ).hexdigest()

    # Persist before returning so the same token survives retries.
    self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, False)
    return token

  def _verifyCustomDomainDNS(self, instance_reference, custom_domain, validation_entry=None):
    """
    Grouped DNS verification steps for custom domain.
    Handles token generation, DNS checking, and validation status updates.

    Args:
      instance_reference: Instance reference
      custom_domain: Custom domain to verify
      validation_entry: Existing validation entry (if any)

    Returns:
      tuple: (is_valid, error_message, validation_info)
        - is_valid: True if DNS verification passed
        - error_message: Error message if validation failed, None otherwise
        - validation_info: Dict with validation instructions or error details
    """
    # Generate or reuse token
    token = self._getOrGenerateToken(instance_reference, custom_domain, validation_entry)

    # Check DNS
    if self._check_custom_domain(custom_domain, token):
      # DNS verification passed - mark as validated
      self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, True)
      return True, None, {}
    else:
      # DNS verification failed - mark as not validated
      self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, False)
      challenge_domain = '%s.%s' % (self.dns_entry_name, custom_domain)
      error_message = (
        'Custom domain verification failed. '
        'Please add TXT record "%s" with value "%s".'
        % (challenge_domain, token)
      )
      validation_info = {
        'txt_record': challenge_domain,
        'txt_value': token,
        'message': error_message
      }
      return False, error_message, validation_info

  def shouldDestroyInstance(self, instance_reference):
    """
    Decide whether a disappeared instance should be destroyed, applying
    retention delay logic. During retention, the instance stays in the DB
    as 'stopped' and its domain_validation entry is preserved (with
    validated=False) so a returning instance can reclaim the domain
    without DNS re-challenge.

    Returns True if the instance should be destroyed, False to keep it.
    """
    if self.instance_retention_delay <= 0:
      return True

    existing = self.requestinstance_db.getInstance(instance_reference)
    if existing is None:
      return True

    if existing['valid_parameter'] == 'stopped':
      # Already in retention — check expiry
      disappeared_at = int(existing['timestamp'])
      if time.time() - disappeared_at >= self.instance_retention_delay:
        return True  # Retention expired → destroy
      self._already_retained_references.add(instance_reference)
      return False  # Still within retention → keep

    # First disappearance — enter retention
    # Preserve domain_validation entry but set validated=False
    validation_entry = self.domain_validation_db.getDomainValidationForInstance(instance_reference)
    if validation_entry:
      self.domain_validation_db.setDomainValidation(
        instance_reference, validation_entry['domain'],
        validation_entry['token'], False)
    # Clear used_hosts so the domain can be claimed by others
    self.domain_validation_db.execute(
      "DELETE FROM used_hosts WHERE instance_reference=?",
      (instance_reference,))
    # Mark as stopped (timestamp is updated by setInstanceState)
    self.requestinstance_db.setInstanceState(instance_reference, 'stopped')
    return False

  def _processDestroyedInstance(self, instance_reference):
    """
    Process a destroyed instance: remove the domain validation from the database
    and remove hosts from used_hosts table.
    """
    self.logger.debug('Destroying instance: %s', instance_reference)

    # removeDomainValidationForInstance also clears used_hosts rows.
    self.domain_validation_db.removeDomainValidationForInstance(instance_reference)

    # CDN instances are local-only — never call the master to destroy them.
    try:
      self._removeInstanceFromDB(instance_reference)
    except Exception as e:
      self.logger.error(
        'Failed to remove destroyed CDN instance %s from database: %s',
        instance_reference, e
      )

  def _validate_netloc(self, netloc):
    """
    Validate that netloc is haproxy compatible server netloc.
    Reuses logic from software/rapid-cdn/software.py
    """
    parsed = urlparse('scheme://' + netloc)
    if ':' in parsed.hostname:
      hostname = '[%s]' % parsed.hostname
    else:
      hostname = parsed.hostname
    return netloc == '%s:%s' % (hostname, parsed.port)

  def _validate_domain(self, domain):
    """
    Validate domain name format.
    Basic validation: should contain only letters, numbers, dots, and hyphens.
    """
    if not domain:
      return False
    # Letters/digits/dots/hyphens; labels cannot start or end with `-`.
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, domain))

  def _get_root_domain(self, domain):
    """
    Extract root domain from a domain name.
    For example: 'www.example.com' -> 'example.com', 'example.com' -> 'example.com'

    Args:
      domain: Domain name

    Returns:
      Root domain (last two parts)
    """
    if not domain:
      return None
    parts = domain.split('.')
    if len(parts) < 2:
      return domain
    return '.'.join(parts[-2:])

  def _validate_cipher(self, cipher, warning_list):
    """
    Validate cipher against GOOD_CIPHER_LIST and CIPHER_TRANSLATION_DICT.
    Returns True if valid, False otherwise.
    Adds warnings to warning_list if cipher is translatable.
    """
    if cipher in GOOD_CIPHER_LIST:
      return True
    if cipher in CIPHER_TRANSLATION_DICT:
      warning_list.append('Cipher %r translated to %r' % (cipher, CIPHER_TRANSLATION_DICT[cipher]))
      return True
    return False

  def _validate_ssl_certificate(self, cert_content):
    """
    Validate SSL certificate using openssl.
    Returns True if valid, False otherwise.
    """
    if not self.openssl_binary:
      return True  # Skip validation if openssl not available
    if not cert_content:
      return False
    try:
      process = subprocess.Popen(
        [self.openssl_binary, 'x509', '-noout'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE
      )
      stdout, _ = process.communicate(cert_content.encode())
      return process.returncode == 0
    except Exception as e:
      self.logger.warning('SSL certificate validation failed: %s', e)
      return False

  def _validate_ssl_key_cert_match(self, key_content, cert_content):
    """
    Validate that SSL key and certificate match by comparing moduli.
    Returns True if they match, False otherwise.
    """
    if not self.openssl_binary:
      return True  # Skip validation if openssl not available
    if not key_content or not cert_content:
      return False
    try:
      # Get key modulus
      key_process = subprocess.Popen(
        [self.openssl_binary, 'rsa', '-noout', '-modulus'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE
      )
      key_modulus, _ = key_process.communicate(key_content.encode())
      if key_process.returncode != 0:
        return False
      key_modulus = key_modulus.decode().strip()

      # Get certificate modulus
      cert_process = subprocess.Popen(
        [self.openssl_binary, 'x509', '-noout', '-modulus'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE
      )
      cert_modulus, _ = cert_process.communicate(cert_content.encode())
      if cert_process.returncode != 0:
        return False
      cert_modulus = cert_modulus.decode().strip()

      return key_modulus == cert_modulus
    except Exception as e:
      self.logger.warning('SSL key/cert matching validation failed: %s', e)
      return False

  def _extractHostsFromParameters(self, parameters):
    """
    Extract all hosts (custom_domain and server-alias) from instance parameters.

    Args:
      parameters: Instance parameters dict

    Returns:
      set: Set of host names (domains and aliases)
    """
    hosts = set()

    custom_domain = parameters.get('custom_domain')
    if custom_domain:
      hosts.add(custom_domain)

    server_alias = parameters.get('server-alias', '')
    if server_alias:
      for alias in server_alias.split():
        # Strip leading `*.` so wildcard aliases match a real host name.
        if alias.startswith('*.'):
          clean_alias = alias[2:]
        else:
          clean_alias = alias
        if clean_alias:
          hosts.add(clean_alias)

    return hosts

  def _validate_server_alias(self, instance_reference, parameters, error_list):
    """
    Validate server-alias domains and check for conflicts.
    Also handles cleanup of old hosts when server-alias changes.

    Args:
      instance_reference: Instance reference
      parameters: Instance parameters dict
      error_list: List to append validation errors to (modified in place)
    """
    # Check if server-alias changed and remove old hosts if needed
    # This must happen before validation to ensure conflict checks use current data
    existing_instance = self.requestinstance_db.getInstance(instance_reference)
    if existing_instance and existing_instance['json_parameters']:
      try:
        existing_params = json.loads(existing_instance['json_parameters'])
        existing_server_alias = existing_params.get('server-alias', '')
        new_server_alias = parameters.get('server-alias', '')

        # Remove hosts if server-alias changed (hosts will be re-added after validation if it passes)
        if existing_server_alias != new_server_alias:
          self.domain_validation_db.execute(
            "DELETE FROM used_hosts WHERE instance_reference=?",
            (instance_reference,)
          )
      except (ValueError, TypeError):
        pass  # Skip if parameters can't be parsed

    custom_domain = parameters.get('custom_domain', '')
    server_alias = parameters.get('server-alias', '')

    if not server_alias:
      return

    # server-alias requires custom_domain
    if not custom_domain:
      error_list.append('server-alias requires custom_domain to be set')
      return

    # Get root domain from custom_domain for server-alias validation
    custom_root_domain = self._get_root_domain(custom_domain)
    server_alias_list = server_alias.split()
    unclashed_aliases = []

    for alias in server_alias_list:
      # Handle wildcard domains (e.g., *.example.com)
      if alias.startswith('*.'):
        clean_alias = alias[2:]
      else:
        clean_alias = alias

      # Validate domain format
      if not self._validate_domain(clean_alias):
        error_list.append('server-alias \'%s\' not valid' % (alias,))
        continue

      # Check if server-alias is part of the same root domain as custom_domain
      alias_root_domain = self._get_root_domain(clean_alias)
      if alias_root_domain != custom_root_domain:
        error_list.append('server-alias \'%s\' must be part of the same root domain as custom_domain (%s)' % (alias, custom_root_domain))
        continue

      # Check if alias matches current instance's custom_domain (allowed)
      if alias == custom_domain:
        unclashed_aliases.append(alias)
        continue

      # Check if alias is already in unclashed list (duplicate in same instance)
      if alias in unclashed_aliases:
        continue

      # Check for conflicts using indexed database lookup (O(log n) per host)
      if self.domain_validation_db.isHostUsedByOtherInstance(clean_alias, instance_reference):
        error_list.append('server-alias \'%s\' clashes' % (alias,))
      else:
        unclashed_aliases.append(alias)

  def preDeployInstanceValidation(self, instance_reference, parameters):
    """
    Validate instance parameters and custom domain ownership.

    Schema validation is handled by slapconfiguration, so we skip it here.
    This method performs additional validations that can't be done in JSON schema:
    - Custom domain DNS verification
    - server-alias domain validation and conflict detection
    - url-netloc-list validation

    Returns:
      tuple: (is_valid, error_list, validation_info)
        - is_valid: Boolean indicating if validation passed
        - error_list: List of error messages (empty if valid)
        - validation_info: Dict of validation instructions or error details
    """
    error_list = []
    warning_list = []

    self._validate_server_alias(instance_reference, parameters, error_list)

    for url_key in ['url-netloc-list', 'https-url-netloc-list', 'health-check-failover-url-netloc-list', 'health-check-failover-https-url-netloc-list']:
      if url_key in parameters and parameters[url_key]:
        for netloc in parameters[url_key].split():
          if not self._validate_netloc(netloc):
            error_list.append('slave %s %r invalid' % (url_key, netloc))

    ciphers = parameters.get('ciphers', '')
    if ciphers:
      cipher_list = ciphers.strip().split()
      for cipher in cipher_list:
        if not self._validate_cipher(cipher, warning_list):
          error_list.append('Cipher %r is not supported.' % (cipher,))

    for cert_key in ['ssl_proxy_ca_crt', 'health-check-failover-ssl-proxy-ca-crt']:
      if cert_key in parameters:
        cert_content = parameters.get(cert_key, '') or ''
        if cert_content and not self._validate_ssl_certificate(cert_content):
          error_list.append('%s is invalid' % (cert_key,))

    # Deprecated ssl_key/ssl_crt/ssl_ca_crt: they must come as a matching trio.
    ssl_key = parameters.get('ssl_key', '')
    ssl_crt = parameters.get('ssl_crt', '')
    ssl_ca_crt = parameters.get('ssl_ca_crt', '')

    if ssl_ca_crt and not (ssl_crt and ssl_key):
      error_list.append('ssl_ca_crt is present, so ssl_crt and ssl_key are required')

    if ssl_key and ssl_crt:
      if not self._validate_ssl_key_cert_match(ssl_key, ssl_crt):
        error_list.append('slave ssl_key and ssl_crt does not match')

    for warning in warning_list:
      self.logger.warning('Instance %s: %s', instance_reference, warning)

    if error_list:
      return False, error_list, {
        'message': '; '.join(error_list),
        'errors': error_list
      }

    # Custom domain verification
    custom_domain = parameters.get('custom_domain')
    if not custom_domain:
      #  Nothing to do
      return True, [], {}

    # Check if domain is already validated for this instance
    validation_entry = self.domain_validation_db.getDomainValidationForInstance(instance_reference)
    if validation_entry and validation_entry['domain'] == custom_domain and validation_entry['validated']:
      # Domain is already validated for this instance
      # All validations passed, store aliases in DB
      instance_hosts = self._extractHostsFromParameters(parameters)
      self.domain_validation_db.addUsedHosts(instance_reference, instance_hosts)
      return True, [], {}

    # Check if domain is different from the one in the database, in that case remove the entry
    if validation_entry and validation_entry['domain'] != custom_domain:
      # Domain changed - remove old entry (this also removes old hosts)
      self.domain_validation_db.removeDomainValidationForInstance(instance_reference)
      validation_entry = None

    # Check if instance is returning from retention with preserved domain
    if (validation_entry and validation_entry['domain'] == custom_domain
        and not validation_entry['validated']):
      existing_instance = self.requestinstance_db.getInstance(instance_reference)
      if existing_instance and existing_instance['valid_parameter'] == 'stopped':
        # Only restore for instances returning from retention
        other = self.domain_validation_db.getValidatedDomainForOtherInstance(
          custom_domain, instance_reference)
        if not other:
          # No one else claimed it — restore validation without DNS re-challenge
          self.domain_validation_db.setDomainValidation(
            instance_reference, custom_domain, validation_entry['token'], True)
          instance_hosts = self._extractHostsFromParameters(parameters)
          self.domain_validation_db.addUsedHosts(instance_reference, instance_hosts)
          return True, [], {}
        # else: someone else owns it — fall through to conflict check below

    # Check if domain is already validated for another instance
    other_instance_entry = self.domain_validation_db.getValidatedDomainForOtherInstance(
      custom_domain, instance_reference
    )
    # If domain is already validated for another instance, return an error
    if other_instance_entry:
      error_message = (
        'Your domain "%s" can not be validated. '
        'Please contact support.'
        % (custom_domain)
      )
      return False, [error_message], {
        'message': error_message,
        'domain': custom_domain
      }

    # Perform DNS verification (grouped function)
    is_valid, error_message, validation_info = self._verifyCustomDomainDNS(
      instance_reference, custom_domain, validation_entry
    )

    if is_valid:
      # DNS verification passed - store aliases in DB now that everything is validated
      instance_hosts = self._extractHostsFromParameters(parameters)
      self.domain_validation_db.addUsedHosts(instance_reference, instance_hosts)
      return True, [], {}
    else:
      # DNS verification failed
      return False, [error_message], validation_info

  def deployInstance(self, instance_reference, instance_data):
    """
    Override deployInstance to skip actual request to master.
    CDN instances are not requested through the normal flow.
    """
    self.logger.debug(
      'Skipping instance request for CDN instance %s (no request to master)',
      instance_reference
    )
    # Return success without making any request
    return True, [], {}

  def postDeployInstanceValidation(self, instance_reference, instance_data, publish_information):
    """
    Verify the slave is in its desired post-deploy state. For CDN
    instances this currently means: master's
    ``instance-publish-slave-information.cfg`` already contains the
    ``[publish-<reference>]`` section.

    When the section is absent the validation reports invalid AND
    signals ``needs_bang=True`` so the master is forced to re-render
    until the frontend's published slave-instance-information-list has
    propagated. The bang signal is the publish-file race's escape hatch:
    without it, the row would settle as unchanged-invalid, the
    timestamp-fallback in instanceNodePostProcessing would see no
    change, and master would never wake up.
    """
    is_valid, error_message, validation_info = self._check_slave_publish_state(
      instance_reference)
    if not is_valid:
      return False, [error_message], validation_info, True
    return True, [], publish_information, False

  def _publishConnectionParameters(self, instance_reference, conn_params):
    """
    Override to prevent calling setConnectionDict.
    CDN instances do not publish connection parameters to the master.
    """
    pass

  def publishInstanceInformation(self, instance_reference, publish_information):
    """
    Override to prevent publishing connection parameters on success.
    CDN instances should not publish connection parameters when successful.
    """
    # No-op: don't publish connection parameters for successful CDN instances
    pass

  def instanceNodePostProcessing(self):
    """
    Post processing for the instance node.
    Triggers bang when instances have changed so the master partition
    re-reads validated-instance-db-path via slapconfiguration.instancenode.deferred.
    """
    needs_bang = False
    # Use the comparison result to detect added, modified, or removed
    # instances. This avoids a same-second race between the slapgrid
    # timestamp and the DB write timestamp, and also catches removed
    # instances (which are deleted from the DB and invisible to a
    # timestamp query).
    comparison = getattr(self, '_comparison', None)
    if comparison:
      # Exclude instances that were already in retention (not first disappearance)
      # from the removed set to avoid triggering bang every cycle during retention
      effective_removed = set(comparison.get('removed', [])) - self._already_retained_references
      if (comparison.get('added') or
          comparison.get('modified') or
          effective_removed):
        needs_bang = True
    if not needs_bang:
      # Unchanged invalid instances that changed validity after
      # reprocessing are only detectable via a timestamp comparison.
      timestamp_int = int(self.timestamp)
      changed_instance = self.requestinstance_db.db.fetchOne(
        "SELECT * FROM instance WHERE CAST(timestamp AS INTEGER) > ?",
        (timestamp_int,)
      )
      if changed_instance:
        needs_bang = True
    if not needs_bang and getattr(self, '_post_deploy_bang_requested', False):
      # A postDeployInstanceValidation call asked for a bang even though
      # the comparison/timestamp signals are silent. The publish-file
      # race is the motivating case: an unchanged-invalid row whose
      # state will only clear once the master rebuilds.
      needs_bang = True
    if needs_bang:
      computer_partition = self._getComputerPartition()
      computer_partition.bang(message='CDN instances have been deployed and instance need reprocessing')

def main():
  """
  Main entry point for command-line execution.
  """
  try:
    args = parse_command_line_args()
    options, pidfile_lock = load_config_and_create_objects(
      args.cfg,
      args.pidfile,
      section_name='slaposinstancenode'
    )

    # Command-line arguments take precedence over config file options.
    logfile = args.logfile or options.get('logfile')
    debug = args.debug or options.get('debug', 'false').lower() in ['y', 'yes', '1', 'true']
    configure_logging(logfile=logfile, debug=debug)

    if pidfile_lock:
      with pidfile_lock:
        recipe = Recipe(
          buildout=None,
          name='cdn-instance-node',
          options=options
        )
        recipe.install()
    else:
      recipe = Recipe(
        buildout=None,
        name='cdn-instance-node',
        options=options
      )
      recipe.install()

    return 0
  except KeyboardInterrupt:
    sys.stderr.write('\nInterrupted by user\n')
    return 130
  except SystemExit as e:
    raise
  except Exception as e:
    sys.stderr.write('Error: %s\n' % str(e))
    import traceback
    traceback.print_exc()
    return 1


if __name__ == '__main__':
  sys.exit(main())
