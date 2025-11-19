import dns.resolver
import hmac
import hashlib
import time
import secrets
from slapos.recipe.requestinstancelist import Recipe as RequestInstanceListRecipe
from slapos.recipe.hostedinstancedb import LocalDBAccessor

class DomainValidationDB(LocalDBAccessor):
  schema = """CREATE TABLE IF NOT EXISTS domain_validation (
    instance_reference VARCHAR(255),
    domain VARCHAR(255),
    token VARCHAR(255),
    validated BOOLEAN,
    timestamp VARCHAR(255),
    PRIMARY KEY (instance_reference, domain)
    );
    CREATE INDEX IF NOT EXISTS idx_instance_reference ON domain_validation(instance_reference);"""

  def __init__(self, db_path):
    super(DomainValidationDB, self).__init__(db_path, self.schema)

  def getDomainValidation(self, instance_reference, domain):
    row = self.fetchOne(
      "SELECT * FROM domain_validation WHERE instance_reference=? AND domain=?",
      (instance_reference, domain)
    )
    return row

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

  def _generateToken(self, instance_reference, custom_domain):
    """
    Generate a non-deterministic token for domain validation.
    Token includes instance_reference, custom_domain, and a random element.
    """
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

    return token

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
    if custom_domain:
      # Check if validation entry exists for this instance-domain pair
      validation_entry = self.domain_validation_db.getDomainValidation(instance_reference, custom_domain)

      if validation_entry:
        # Token already exists - reuse it
        token = validation_entry['token']
        # Convert integer to boolean (SQLite stores BOOLEAN as 0/1)
        is_validated = bool(validation_entry['validated'])
        if is_validated:
          # Already validated - no need to re-check DNS
          return True, [], {}
      else:
        # Generate new token for this instance-domain pair
        token = self._generateToken(instance_reference, custom_domain)
        # Store the token (not yet validated)
        self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, False)

      # Check DNS
      if not self._check_custom_domain(custom_domain, token):
        # Validation failed - update DB with failure status
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

      # Validation successful - update DB with success status
      self.domain_validation_db.setDomainValidation(instance_reference, custom_domain, token, True)

    return True, [], {}
