import unittest
import mock
from slapos.recipe import cdnrequest
import dns.resolver

class TestCDNRequestRecipe(unittest.TestCase):

  def setUp(self):
    self.buildout = {
      "buildout": {},
    }
    self.options = {
      'instance-db-path': '/tmp/instance.db',
      'domainvalidation-db-path': '/tmp/domainvalidation.db',
      'requestinstance-db-path': '/tmp/requestinstance.db',
      'server-url': 'http://test.example.com',
      'computer-id': 'test-computer',
      'partition-id': 'test-partition',
      'software-url': 'http://test.example.com/software',
      'software-type': 'default',
      'verification-secret': 'test-secret'
    }
    # Mock databases to avoid file creation
    self.mock_instance_db = mock.MagicMock()
    self.mock_requestinstance_db = mock.MagicMock()
    self.mock_domain_validation_db = mock.MagicMock()

    # Patch HostedInstanceLocalDB to return mocks
    self.db_patch = mock.patch('slapos.recipe.requestinstancelist.HostedInstanceLocalDB')
    self.MockDB = self.db_patch.start()
    self.MockDB.side_effect = [self.mock_instance_db, self.mock_requestinstance_db]

    # Patch DomainValidationDB
    self.dv_db_patch = mock.patch('slapos.recipe.cdnrequest.DomainValidationDB')
    self.MockDVDB = self.dv_db_patch.start()
    self.MockDVDB.return_value = self.mock_domain_validation_db

  def tearDown(self):
    self.db_patch.stop()
    self.dv_db_patch.stop()

  def test_validate_no_custom_domain(self):
    """Test validation when custom_domain is not provided"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Should be valid if no custom_domain (nothing to verify)
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', {})
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])
    self.assertEqual(conn_params, {})

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_success(self, MockResolver):
    """Test successful validation of custom domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Mock DB methods - no existing validation entry
    self.mock_domain_validation_db.getDomainValidation.return_value = None

    # Setup mock DNS response
    mock_answer = mock.MagicMock()
    mock_rdata = mock.MagicMock()
    # Token will be generated, so we'll capture it from the setDomainValidation call
    # For now, use a placeholder that will be replaced
    mock_rdata.strings = [b'placeholder-token']

    mock_answer.__iter__.return_value = iter([mock_rdata])
    mock_resolver_instance.resolve.return_value = mock_answer

    # Capture the token that gets generated
    generated_token = [None]
    def capture_token(instance_ref, domain, token, validated):
      generated_token[0] = token
      # Update mock to return this token for subsequent DNS checks
      mock_rdata.strings = [token.encode('utf-8')]

    self.mock_domain_validation_db.setDomainValidation.side_effect = capture_token

    is_valid, error_list, conn_params = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])
    self.assertEqual(conn_params, {})

    # Verify DNS lookup was called with the default dns-entry-name
    mock_resolver_instance.resolve.assert_called_with('_slapos-challenge.example.com', 'TXT')
    # Verify DB was called with instance_reference, domain, token, and validated=True
    self.mock_domain_validation_db.setDomainValidation.assert_called()
    call_args = self.mock_domain_validation_db.setDomainValidation.call_args
    self.assertEqual(call_args[0][0], 'ref1')  # instance_reference
    self.assertEqual(call_args[0][1], 'example.com')  # domain
    self.assertIsNotNone(call_args[0][2])  # token (generated)
    self.assertTrue(call_args[0][3])  # validated=True

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_failure_wrong_token(self, MockResolver):
    """Test validation failure when token doesn't match"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Mock DB methods - no existing validation entry
    self.mock_domain_validation_db.getDomainValidation.return_value = None

    # Setup mock DNS response with wrong token
    mock_answer = mock.MagicMock()
    mock_rdata = mock.MagicMock()
    mock_rdata.strings = [b'wrong-token']

    mock_answer.__iter__.return_value = iter([mock_rdata])
    mock_resolver_instance.resolve.return_value = mock_answer

    is_valid, error_list, conn_params = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertEqual(len(error_list), 1)
    self.assertIn('Custom domain verification failed', error_list[0])
    self.assertIn('txt_record', conn_params)
    self.assertIn('txt_value', conn_params)
    self.assertEqual(conn_params['txt_record'], '_slapos-challenge.example.com')

    # Verify DB update (failure) - called twice: once when generating token, once when validation fails
    self.assertTrue(self.mock_domain_validation_db.setDomainValidation.called)
    # Last call should be with validated=False
    last_call = self.mock_domain_validation_db.setDomainValidation.call_args_list[-1]
    self.assertEqual(last_call[0][0], 'ref1')  # instance_reference
    self.assertEqual(last_call[0][1], 'example.com')  # domain
    self.assertIsNotNone(last_call[0][2])  # token
    self.assertFalse(last_call[0][3])  # validated=False

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_failure_no_record(self, MockResolver):
    """Test validation failure when DNS record is missing"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Mock DB methods - no existing validation entry
    self.mock_domain_validation_db.getDomainValidation.return_value = None

    # Setup mock DNS to raise NXDOMAIN
    mock_resolver_instance.resolve.side_effect = dns.resolver.NXDOMAIN

    is_valid, error_list, conn_params = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertIn('txt_record', conn_params)
    self.assertIn('txt_value', conn_params)
    self.assertEqual(conn_params['txt_record'], '_slapos-challenge.example.com')

    # Verify DB update (failure) - called twice: once when generating token, once when validation fails
    self.assertTrue(self.mock_domain_validation_db.setDomainValidation.called)
    # Last call should be with validated=False
    last_call = self.mock_domain_validation_db.setDomainValidation.call_args_list[-1]
    self.assertEqual(last_call[0][0], 'ref1')  # instance_reference
    self.assertEqual(last_call[0][1], 'example.com')  # domain
    self.assertIsNotNone(last_call[0][2])  # token
    self.assertFalse(last_call[0][3])  # validated=False

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_failure_timeout(self, MockResolver):
    """Test validation failure when DNS lookup times out"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Mock DB methods - no existing validation entry
    self.mock_domain_validation_db.getDomainValidation.return_value = None

    # Setup mock DNS to raise Timeout
    mock_resolver_instance.resolve.side_effect = dns.resolver.LifetimeTimeout

    is_valid, error_list, conn_params = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertIn('txt_record', conn_params)
    self.assertEqual(conn_params['txt_record'], '_slapos-challenge.example.com')

    # Verify DB update (failure) - called twice: once when generating token, once when validation fails
    self.assertTrue(self.mock_domain_validation_db.setDomainValidation.called)
    # Last call should be with validated=False
    last_call = self.mock_domain_validation_db.setDomainValidation.call_args_list[-1]
    self.assertEqual(last_call[0][0], 'ref1')  # instance_reference
    self.assertEqual(last_call[0][1], 'example.com')  # domain
    self.assertIsNotNone(last_call[0][2])  # token
    self.assertFalse(last_call[0][3])  # validated=False

  def test_validate_custom_domain_already_validated(self):
    """Test that validation is skipped if already validated in DB"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DB to return valid entry for this instance-domain pair
    # Note: SQLite stores BOOLEAN as integers (0/1), but we convert to bool in code
    stored_token = 'stored-token-12345'
    self.mock_domain_validation_db.getDomainValidation.return_value = {
      'instance_reference': 'ref1',
      'domain': 'example.com',
      'validated': 1,  # SQLite returns 1 for True
      'token': stored_token
    }

    # We don't mock resolve here, so if it calls resolve it will fail (or we can mock it to assert not called)
    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      is_valid, error_list, conn_params = recipe.validateInstance(
        'ref1',
        {'custom_domain': 'example.com'}
      )

      self.assertTrue(is_valid)
      self.assertEqual(error_list, [])
      self.assertEqual(conn_params, {})

      # Verify getDomainValidation was called with instance_reference and domain
      self.mock_domain_validation_db.getDomainValidation.assert_called_with('ref1', 'example.com')
      # Verify DNS lookup was NOT called (already validated)
      mock_resolver_instance.resolve.assert_not_called()
      # Verify setDomainValidation was NOT called (no update needed)
      self.mock_domain_validation_db.setDomainValidation.assert_not_called()

  def test_validate_custom_domain_token_reuse(self):
    """Test that token is reused if entry exists but not yet validated"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DB to return entry that exists but is not yet validated
    stored_token = 'stored-token-67890'
    self.mock_domain_validation_db.getDomainValidation.return_value = {
      'instance_reference': 'ref1',
      'domain': 'example.com',
      'validated': 0,  # SQLite returns 0 for False
      'token': stored_token
    }

    # Setup mock DNS response with the stored token
    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      mock_answer = mock.MagicMock()
      mock_rdata = mock.MagicMock()
      mock_rdata.strings = [stored_token.encode('utf-8')]
      mock_answer.__iter__.return_value = iter([mock_rdata])
      mock_resolver_instance.resolve.return_value = mock_answer

      is_valid, error_list, conn_params = recipe.validateInstance(
        'ref1',
        {'custom_domain': 'example.com'}
      )

      self.assertTrue(is_valid)
      self.assertEqual(error_list, [])
      self.assertEqual(conn_params, {})

      # Verify getDomainValidation was called
      self.mock_domain_validation_db.getDomainValidation.assert_called_with('ref1', 'example.com')
      # Verify DNS lookup was called with the stored token
      mock_resolver_instance.resolve.assert_called_with('_slapos-challenge.example.com', 'TXT')
      # Verify setDomainValidation was called to update status to validated=True
      self.mock_domain_validation_db.setDomainValidation.assert_called_with(
        'ref1', 'example.com', stored_token, True
      )

  def test_validate_custom_domain_dns_entry_name_configurable(self):
    """Test that dns-entry-name option is respected"""
    self.options['dns-entry-name'] = 'custom-challenge'
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DB methods
    self.mock_domain_validation_db.getDomainValidation.return_value = None

    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      mock_answer = mock.MagicMock()
      mock_rdata = mock.MagicMock()
      mock_rdata.strings = [b'test-token']
      mock_answer.__iter__.return_value = iter([mock_rdata])
      mock_resolver_instance.resolve.return_value = mock_answer

      recipe.validateInstance('ref1', {'custom_domain': 'example.com'})

      # Verify DNS lookup used custom dns-entry-name
      mock_resolver_instance.resolve.assert_called_with('custom-challenge.example.com', 'TXT')
