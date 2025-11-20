import dns.resolver
import hmac
import hashlib
import time
import secrets
import re
import urllib.parse
import subprocess
from slapos.recipe.requestinstancelist import Recipe as RequestInstanceListRecipe
from slapos.recipe.hostedinstancedb import LocalDBAccessor

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
    CREATE INDEX IF NOT EXISTS idx_instance_reference ON domain_validation(instance_reference);"""

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
    """
    self.execute(
      "DELETE FROM domain_validation WHERE instance_reference=?",
      (instance_reference,)
    )

  def setDomainValidation(self, instance_reference, domain, token, validated):
    timestamp = str(int(time.time()))
    self.execute(
      "INSERT OR REPLACE INTO domain_validation VALUES (?, ?, ?, ?, ?)",
      (instance_reference, domain, token, validated, timestamp)
    )

class CDNRequestRecipe(RequestInstanceListRecipe):
  """
  RequestInstanceListRecipe with custom domain verification for CDN.
  """

  def __init__(self, buildout, name, options):
    super(CDNRequestRecipe, self).__init__(buildout, name, options)
    self.dns_entry_name = options.get('dns-entry-name', '_slapos-challenge')
    self.domain_validation_db = DomainValidationDB(self.options['domainvalidation-db-path'])
    # Get openssl binary from options (required for SSL validation)
    self.openssl_binary = options.get('openssl-binary')
    if not self.openssl_binary:
      self.logger.warning('openssl-binary option not provided, SSL certificate validation will be skipped')

  def _check_custom_domain(self, domain, token):
    """
    Check if the custom domain has the required TXT record.
    """
    challenge_domain = '%s.%s' % (self.dns_entry_name, domain)
    try:
      resolver = dns.resolver.Resolver()
      # Configure resolver if needed, e.g. timeout
      resolver.lifetime = 5.0
      answers = resolver.resolve(challenge_domain, 'TXT')
      for rdata in answers:
        # TXT records can contain multiple strings, join them
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
      # Reuse existing token (domain matches, but validation may not be complete)
      return validation_entry['token']

    # Generate random component
    random_component = secrets.token_hex(16)  # 32 hex characters

    # Create token using HMAC-SHA256 with instance_reference, domain, and random component
    secret = self.options.get('verification-secret', 'slapos-cdn-secret')
    message = '%s:%s:%s' % (instance_reference, custom_domain, random_component)
    key = secret.encode('utf-8')

    token = hmac.new(
      key,
      message.encode('utf-8'),
      hashlib.sha256
    ).hexdigest()

    # Store the token to prevent regeneration
    self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, False)
    return token

  def _processDestroyedInstance(self, instance_reference):
    """
    Process a destroyed instance: remove the domain validation from the database.
    """
    self.logger.debug('Destroying instance: %s', instance_reference)
    self.domain_validation_db.removeDomainValidationForInstance(instance_reference)
    super(CDNRequestRecipe, self)._processDestroyedInstance(instance_reference)

  def _validate_netloc(self, netloc):
    """
    Validate that netloc is haproxy compatible server netloc.
    Reuses logic from software/rapid-cdn/software.py
    """
    parsed = urllib.parse.urlparse('scheme://' + netloc)
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
    # Basic domain validation: letters, numbers, dots, hyphens
    # Must not start or end with dot or hyphen
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, domain))

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

  def validateInstance(self, instance_reference, parameters):
    """
    Validate instance parameters and custom domain ownership.

    Schema validation is handled by slapconfiguration, so we skip it here.
    This method performs additional validations that can't be done in JSON schema:
    - Custom domain DNS verification
    - server-alias domain validation
    - url-netloc-list validation

    Returns:
      tuple: (is_valid, error_list, conn_params)
        - is_valid: Boolean indicating if validation passed
        - error_list: List of error messages (empty if valid)
        - conn_params: Dict of connection parameters or validation instructions
    """
    error_list = []
    warning_list = []

    # Validate server-alias domains
    server_alias = parameters.get('server-alias', '')
    if server_alias:
      for alias in server_alias.split():
        # Handle wildcard domains (e.g., *.example.com)
        if alias.startswith('*.'):
          clean_alias = alias[2:]
        else:
          clean_alias = alias
        if not self._validate_domain(clean_alias):
          error_list.append('server-alias \'%s\' not valid' % (alias,))

    # Validate url-netloc-list fields
    for url_key in ['url-netloc-list', 'https-url-netloc-list', 'health-check-failover-url-netloc-list', 'health-check-failover-https-url-netloc-list']:
      if url_key in parameters and parameters[url_key]:
        for netloc in parameters[url_key].split():
          if not self._validate_netloc(netloc):
            error_list.append('slave %s %r invalid' % (url_key, netloc))

    # Validate ciphers
    ciphers = parameters.get('ciphers', '')
    if ciphers:
      cipher_list = ciphers.strip().split()
      for cipher in cipher_list:
        if not self._validate_cipher(cipher, warning_list):
          error_list.append('Cipher %r is not supported.' % (cipher,))

    # Validate SSL certificates
    for cert_key in ['ssl_proxy_ca_crt', 'health-check-failover-ssl-proxy-ca-crt']:
      if cert_key in parameters:
        cert_content = parameters.get(cert_key, '') or ''
        if cert_content and not self._validate_ssl_certificate(cert_content):
          error_list.append('%s is invalid' % (cert_key,))

    # Validate SSL key/cert matching (for deprecated ssl_key/ssl_crt)
    ssl_key = parameters.get('ssl_key', '')
    ssl_crt = parameters.get('ssl_crt', '')
    ssl_ca_crt = parameters.get('ssl_ca_crt', '')

    # Check if ssl_ca_crt is present without ssl_crt and ssl_key
    if ssl_ca_crt and not (ssl_crt and ssl_key):
      error_list.append('ssl_ca_crt is present, so ssl_crt and ssl_key are required')

    # Check if ssl_key and ssl_crt match
    if ssl_key and ssl_crt:
      if not self._validate_ssl_key_cert_match(ssl_key, ssl_crt):
        error_list.append('slave ssl_key and ssl_crt does not match')

    # Log warnings (cipher translations)
    for warning in warning_list:
      self.logger.warning('Instance %s: %s', instance_reference, warning)

    # If there are validation errors, return them
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
      return True, [], {}

    # Check if domain is different from the one in the database, in that case remove the entry
    if validation_entry and validation_entry['domain'] != custom_domain:
      self.domain_validation_db.removeDomainValidationForInstance(instance_reference)
      validation_entry = None

    # Check if domain is already validated for another instance
    other_instance_entry = self.domain_validation_db.getValidatedDomainForOtherInstance(
      custom_domain, instance_reference
    )
    # If domain is already validated for another instance, return an error
    if other_instance_entry:
      error_message = (
        'Custom domain "%s" is already used and validated. '
        'Each domain can only be validated for one instance.'
        % (custom_domain)
      )
      return False, [error_message], {
        'message': error_message,
        'domain': custom_domain
      }

    token = self._getOrGenerateToken(instance_reference, custom_domain, validation_entry)

    # Check DNS
    if self._check_custom_domain(custom_domain, token):
      self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, True)
      return True, [], {}

    self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, False)

    challenge_domain = '%s.%s' % (self.dns_entry_name, custom_domain)
    error_message = (
      'Custom domain verification failed. '
      'Please add TXT record "%s" with value "%s".'
      % (challenge_domain, token)
    )
    return False, [error_message], {
      'txt_record': challenge_domain,
      'txt_value': token,
      'message': error_message
    }
