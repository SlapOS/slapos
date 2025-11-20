import dns.resolver
import hmac
import hashlib
import time
import secrets
from slapos.recipe.requestinstancelist import Recipe as RequestInstanceListRecipe
from slapos.recipe.hostedinstancedb import LocalDBAccessor

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

  def validateInstance(self, instance_reference, parameters):
    """
    Validate instance parameters and custom domain ownership.

    Schema validation is handled by slapconfiguration, so we skip it here.
    This method only performs custom domain verification.

    Returns:
      tuple: (is_valid, error_list, conn_params)
        - is_valid: Boolean indicating if validation passed
        - error_list: List of error messages (empty if valid)
        - conn_params: Dict of connection parameters or validation instructions
    """
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
