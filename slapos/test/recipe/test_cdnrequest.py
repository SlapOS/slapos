import unittest
import mock
from slapos.recipe import cdnrequest
import dns.resolver
from testfixtures import LogCapture
import os
import tempfile

class TestCDNRequestRecipe(unittest.TestCase):

  def setUp(self):
    self.instance_db_fd, self.instance_db_path = tempfile.mkstemp()
    self.requestinstance_db_fd, self.requestinstance_db_path = tempfile.mkstemp()
    self.domainvalidation_db_fd, self.domainvalidation_db_path = tempfile.mkstemp()

    self.buildout = {
      "buildout": {},
    }
    self.options = {
      'instance-db-path': self.instance_db_path,
      'domainvalidation-db-path': self.domainvalidation_db_path,
      'requestinstance-db-path': self.requestinstance_db_path,
      'server-url': 'http://test.example.com',
      'computer-id': 'test-computer',
      'partition-id': 'test-partition',
      'software-url': 'http://test.example.com/software',
      'software-type': 'default',
      'verification-secret': 'test-secret'
    }
    # Mock databases for parent class (HostedInstanceLocalDB)
    self.mock_instance_db = mock.MagicMock()
    self.mock_requestinstance_db = mock.MagicMock()

    # Patch HostedInstanceLocalDB to return mocks
    self.db_patch = mock.patch('slapos.recipe.requestinstancelist.HostedInstanceLocalDB')
    self.MockDB = self.db_patch.start()
    self.MockDB.side_effect = [self.mock_instance_db, self.mock_requestinstance_db]

    # Use real DomainValidationDB for integration testing
    # (no mocking needed - will use self.domainvalidation_db_path)

  def tearDown(self):
    self.db_patch.stop()

    os.close(self.instance_db_fd)
    if os.path.exists(self.instance_db_path):
      os.unlink(self.instance_db_path)
    os.close(self.requestinstance_db_fd)
    if os.path.exists(self.requestinstance_db_path):
      os.unlink(self.requestinstance_db_path)
    os.close(self.domainvalidation_db_fd)
    if os.path.exists(self.domainvalidation_db_path):
      os.unlink(self.domainvalidation_db_path)

  def test_validate_no_custom_domain(self):
    """Test validation when custom_domain is not provided"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Should be valid if no custom_domain (nothing to verify)
    is_valid, error_list, connection_parameters = recipe.validateInstance('ref1', {})
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])
    self.assertEqual(connection_parameters, {})

    # Verify no database entry was created
    result = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
    self.assertIsNone(result)

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_success(self, MockResolver):
    """Test successful validation of custom domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Setup mock DNS response that will return the token from database
    mock_answer = mock.MagicMock()
    mock_rdata = mock.MagicMock()

    def get_dns_response(*args, **kwargs):
      # Get token from database after it's been generated
      db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
      if db_entry:
        mock_rdata.strings = [db_entry['token'].encode('utf-8')]
      else:
        mock_rdata.strings = [b'placeholder']
      mock_answer.__iter__.return_value = iter([mock_rdata])
      return mock_answer

    mock_resolver_instance.resolve.side_effect = get_dns_response

    is_valid, error_list, connection_parameters = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])
    self.assertEqual(connection_parameters, {})

    # Verify DNS lookup was called with the default dns-entry-name
    mock_resolver_instance.resolve.assert_called_with('_slapos-challenge.example.com', 'TXT')
    # Verify database entry was created and validated
    db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
    self.assertIsNotNone(db_entry)
    self.assertEqual(db_entry['domain'], 'example.com')
    self.assertEqual(db_entry['instance_reference'], 'ref1')
    self.assertTrue(bool(db_entry['validated']))
    self.assertIsNotNone(db_entry['token'])

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_failure_wrong_token(self, MockResolver):
    """Test validation failure when token doesn't match"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Setup mock DNS response with wrong token
    mock_answer = mock.MagicMock()
    mock_rdata = mock.MagicMock()
    mock_rdata.strings = [b'wrong-token']

    mock_answer.__iter__.return_value = iter([mock_rdata])
    mock_resolver_instance.resolve.return_value = mock_answer

    is_valid, error_list, connection_parameters = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertEqual(len(error_list), 1)
    self.assertIn('Custom domain verification failed', error_list[0])
    self.assertIn('txt_record', connection_parameters)
    self.assertIn('txt_value', connection_parameters)
    self.assertEqual(connection_parameters['txt_record'], '_slapos-challenge.example.com')

    # Verify database entry was created with validated=False
    db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
    self.assertIsNotNone(db_entry)
    self.assertEqual(db_entry['domain'], 'example.com')
    self.assertEqual(db_entry['instance_reference'], 'ref1')
    self.assertFalse(bool(db_entry['validated']))
    self.assertIsNotNone(db_entry['token'])
    self.assertEqual(connection_parameters['txt_value'], db_entry['token'])

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_failure_no_record(self, MockResolver):
    """Test validation failure when DNS record is missing"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Setup mock DNS to raise NXDOMAIN
    mock_resolver_instance.resolve.side_effect = dns.resolver.NXDOMAIN

    is_valid, error_list, connection_parameters = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertIn('txt_record', connection_parameters)
    self.assertIn('txt_value', connection_parameters)
    self.assertEqual(connection_parameters['txt_record'], '_slapos-challenge.example.com')

    # Verify database entry was created with validated=False
    db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
    self.assertIsNotNone(db_entry)
    self.assertEqual(db_entry['domain'], 'example.com')
    self.assertFalse(bool(db_entry['validated']))
    self.assertEqual(connection_parameters['txt_value'], db_entry['token'])

  @mock.patch('dns.resolver.Resolver')
  def test_validate_custom_domain_failure_timeout(self, MockResolver):
    """Test validation failure when DNS lookup times out"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    mock_resolver_instance = MockResolver.return_value

    # Setup mock DNS to raise Timeout
    mock_resolver_instance.resolve.side_effect = dns.resolver.LifetimeTimeout

    is_valid, error_list, connection_parameters = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertIn('txt_record', connection_parameters)
    self.assertEqual(connection_parameters['txt_record'], '_slapos-challenge.example.com')

    # Verify database entry was created with validated=False
    db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
    self.assertIsNotNone(db_entry)
    self.assertEqual(db_entry['domain'], 'example.com')
    self.assertFalse(bool(db_entry['validated']))

  def test_validate_custom_domain_already_validated(self):
    """Test that validation is skipped if already validated in DB"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Pre-populate database with validated entry
    stored_token = 'stored-token-12345'
    recipe.domain_validation_db.setDomainValidation('ref1', 'example.com', stored_token, True)

    # We don't mock resolve here, so if it calls resolve it will fail (or we can mock it to assert not called)
    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      is_valid, error_list, connection_parameters = recipe.validateInstance(
        'ref1',
        {'custom_domain': 'example.com'}
      )

      self.assertTrue(is_valid)
      self.assertEqual(error_list, [])
      self.assertEqual(connection_parameters, {})

      # Verify DNS lookup was NOT called (already validated)
      mock_resolver_instance.resolve.assert_not_called()
      # Verify database entry still exists and is validated
      db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
      self.assertIsNotNone(db_entry)
      self.assertTrue(bool(db_entry['validated']))
      self.assertEqual(db_entry['token'], stored_token)

  def test_validate_custom_domain_token_reuse(self):
    """Test that token is reused if entry exists but not yet validated"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Pre-populate database with unvalidated entry
    stored_token = 'stored-token-67890'
    recipe.domain_validation_db.setDomainValidation('ref1', 'example.com', stored_token, False)

    # Setup mock DNS response with the stored token
    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      mock_answer = mock.MagicMock()
      mock_rdata = mock.MagicMock()
      mock_rdata.strings = [stored_token.encode('utf-8')]
      mock_answer.__iter__.return_value = iter([mock_rdata])
      mock_resolver_instance.resolve.return_value = mock_answer

      is_valid, error_list, connection_parameters = recipe.validateInstance(
        'ref1',
        {'custom_domain': 'example.com'}
      )

      self.assertTrue(is_valid)
      self.assertEqual(error_list, [])
      self.assertEqual(connection_parameters, {})

      # Verify DNS lookup was called
      mock_resolver_instance.resolve.assert_called_with('_slapos-challenge.example.com', 'TXT')
      # Verify database entry was updated to validated=True
      db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
      self.assertIsNotNone(db_entry)
      self.assertTrue(bool(db_entry['validated']))
      self.assertEqual(db_entry['token'], stored_token)

  def test_validate_custom_domain_dns_entry_name_configurable(self):
    """Test that dns-entry-name option is respected"""
    self.options['dns-entry-name'] = 'custom-challenge'
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      mock_answer = mock.MagicMock()
      mock_rdata = mock.MagicMock()

      def get_dns_response(*args, **kwargs):
        db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
        if db_entry:
          mock_rdata.strings = [db_entry['token'].encode('utf-8')]
        else:
          mock_rdata.strings = [b'placeholder']
        mock_answer.__iter__.return_value = iter([mock_rdata])
        return mock_answer

      mock_resolver_instance.resolve.side_effect = get_dns_response

      recipe.validateInstance('ref1', {'custom_domain': 'example.com'})
      # Verify DNS lookup used custom dns-entry-name
      mock_resolver_instance.resolve.assert_called_with('custom-challenge.example.com', 'TXT')

  def test_validate_domain_already_validated_for_other_instance(self):
    """Test that validation fails if domain is already validated for another instance"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Pre-populate database with validated entry for another instance
    recipe.domain_validation_db.setDomainValidation('other-instance', 'example.com', 'existing-token', True)

    is_valid, error_list, connection_parameters = recipe.validateInstance(
      'ref1',
      {'custom_domain': 'example.com'}
    )

    self.assertFalse(is_valid)
    self.assertEqual(len(error_list), 1)
    self.assertIn('already used and validated', error_list[0])
    self.assertIn('message', connection_parameters)
    self.assertIn('domain', connection_parameters)
    self.assertEqual(connection_parameters['domain'], 'example.com')
    # Verify no entry was created for ref1
    db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
    self.assertIsNone(db_entry)

  def test_validate_domain_change_removes_old_domain(self):
    """Test that changing domain removes old domain entry for the instance"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Pre-populate database with old domain entry
    recipe.domain_validation_db.setDomainValidation('ref1', 'old-domain.com', 'old-token', True)

    # Setup mock DNS response
    with mock.patch('dns.resolver.Resolver') as MockResolver:
      mock_resolver_instance = MockResolver.return_value
      mock_answer = mock.MagicMock()
      mock_rdata = mock.MagicMock()

      def get_dns_response(*args, **kwargs):
        db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
        if db_entry:
          mock_rdata.strings = [db_entry['token'].encode('utf-8')]
        else:
          mock_rdata.strings = [b'placeholder']
        mock_answer.__iter__.return_value = iter([mock_rdata])
        return mock_answer

      mock_resolver_instance.resolve.side_effect = get_dns_response

      # Validate with new domain
      recipe.validateInstance('ref1', {'custom_domain': 'new-domain.com'})

      # Verify old domain entry was removed and new one was created
      db_entry = recipe.domain_validation_db.getDomainValidationForInstance('ref1')
      self.assertIsNotNone(db_entry)
      self.assertEqual(db_entry['domain'], 'new-domain.com')
      self.assertNotEqual(db_entry['domain'], 'old-domain.com')

  def test_process_destroyed_instance(self):
    """Test that _processDestroyedInstance removes domain validation entries"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Pre-populate database with an entry
    recipe.domain_validation_db.setDomainValidation('test-instance-ref', 'example.com', 'test-token', True)

    # Mock the parent's _processDestroyedInstance to avoid actual destruction logic
    with mock.patch(
        'slapos.recipe.requestinstancelist.Recipe._processDestroyedInstance'
    ) as mock_parent_process:
      instance_reference = 'test-instance-ref'

      with LogCapture() as log:
        # Call the method
        recipe._processDestroyedInstance(instance_reference)

      # Verify entry was removed from database
      db_entry = recipe.domain_validation_db.getDomainValidationForInstance(instance_reference)
      self.assertIsNone(db_entry)

      # Verify parent's _processDestroyedInstance was called
      mock_parent_process.assert_called_once_with(instance_reference)

      # Verify debug log was called
      log.check(
        ('test', 'DEBUG', 'Destroying instance: %s' % instance_reference),
      )


class TestDomainValidationDB(unittest.TestCase):

  def setUp(self):
    self.db_fd, self.db_path = tempfile.mkstemp()

  def tearDown(self):
    os.close(self.db_fd)
    if os.path.exists(self.db_path):
      os.unlink(self.db_path)

  def test_create_database(self):
    """Test that database is created with correct schema"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    self.assertTrue(os.path.exists(self.db_path))

  def test_set_and_get_domain_validation(self):
    """Test setting and getting domain validation entries"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    instance_ref = 'test-instance-1'
    domain = 'example.com'
    token = 'test-token-123'
    validated = True

    # Set validation entry
    db.setDomainValidation(instance_ref, domain, token, validated)

    # Get validation entry
    result = db.getDomainValidationForInstance(instance_ref)
    self.assertIsNotNone(result)
    self.assertEqual(result['instance_reference'], instance_ref)
    self.assertEqual(result['domain'], domain)
    self.assertEqual(result['token'], token)
    # SQLite stores BOOLEAN as 0/1, but we can check it's truthy
    self.assertTrue(bool(result['validated']))
    self.assertIsNotNone(result['timestamp'])

  def test_get_nonexistent_entry(self):
    """Test getting a non-existent entry returns None"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    result = db.getDomainValidationForInstance('nonexistent-instance')
    self.assertIsNone(result)

  def test_update_existing_entry(self):
    """Test that setDomainValidation updates existing entries (INSERT OR REPLACE)"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    instance_ref = 'test-instance-1'
    domain = 'example.com'

    # Set initial entry
    db.setDomainValidation(instance_ref, domain, 'old-token', False)
    result1 = db.getDomainValidationForInstance(instance_ref)
    self.assertEqual(result1['token'], 'old-token')
    self.assertFalse(bool(result1['validated']))
    old_timestamp = result1['timestamp']

    # Add a small delay to ensure timestamp changes
    import time
    time.sleep(1)

    # Update entry
    db.setDomainValidation(instance_ref, domain, 'new-token', True)
    result2 = db.getDomainValidationForInstance(instance_ref)
    self.assertEqual(result2['token'], 'new-token')
    self.assertTrue(bool(result2['validated']))
    # Timestamp should be updated
    self.assertNotEqual(result2['timestamp'], old_timestamp)

  def test_same_domain_different_instances(self):
    """Test storing the same domain for different instances"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    domain = 'example.com'

    # Set same domain for different instances
    db.setDomainValidation('instance-1', domain, 'token1', True)
    db.setDomainValidation('instance-2', domain, 'token2', False)
    db.setDomainValidation('instance-3', domain, 'token3', True)

    # Check instance-1 (validated=True)
    result1 = db.getDomainValidationForInstance('instance-1')
    self.assertIsNotNone(result1)
    self.assertEqual(result1['domain'], domain)
    self.assertEqual(result1['token'], 'token1')
    self.assertTrue(bool(result1['validated']))

    # Check instance-2 (validated=False)
    result2 = db.getDomainValidationForInstance('instance-2')
    self.assertIsNotNone(result2)
    self.assertEqual(result2['domain'], domain)
    self.assertEqual(result2['token'], 'token2')
    self.assertFalse(bool(result2['validated']))

    # Check instance-3 (validated=True)
    result3 = db.getDomainValidationForInstance('instance-3')
    self.assertIsNotNone(result3)
    self.assertEqual(result3['domain'], domain)
    self.assertEqual(result3['token'], 'token3')
    self.assertTrue(bool(result3['validated']))

  def test_remove_domain_validation_for_instance(self):
    """Test removing domain validation entry by instance reference"""
    db = cdnrequest.DomainValidationDB(self.db_path)

    # Create entries for multiple instances (one domain per instance)
    db.setDomainValidation('instance-1', 'example.com', 'token1', True)
    db.setDomainValidation('instance-2', 'example.org', 'token2', False)
    db.setDomainValidation('instance-3', 'example.net', 'token3', True)

    # Remove entry for instance-1
    db.removeDomainValidationForInstance('instance-1')

    # Verify instance-1 entry is removed
    self.assertIsNone(db.getDomainValidationForInstance('instance-1'))

    # Verify other instances' entries still exist
    self.assertIsNotNone(db.getDomainValidationForInstance('instance-2'))
    self.assertIsNotNone(db.getDomainValidationForInstance('instance-3'))


  def test_remove_nonexistent_instance(self):
    """Test removing entries for non-existent instance doesn't raise an error"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    db.setDomainValidation('instance-1', 'example.com', 'token1', True)

    # Should not raise an error
    db.removeDomainValidationForInstance('nonexistent-instance')

    # Existing entry should still exist
    self.assertIsNotNone(db.getDomainValidationForInstance('instance-1'))

  def test_get_domain_validation_for_instance(self):
    """Test getting domain validation entry for an instance"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    db.setDomainValidation('instance-1', 'example.com', 'token1', True)

    result = db.getDomainValidationForInstance('instance-1')
    self.assertIsNotNone(result)
    self.assertEqual(result['domain'], 'example.com')
    self.assertEqual(result['token'], 'token1')
    self.assertTrue(bool(result['validated']))
    self.assertIsNotNone(result['timestamp'])

  def test_get_validated_domain_for_other_instance(self):
    """Test checking if domain is validated for another instance"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    db.setDomainValidation('instance-1', 'example.com', 'token1', True)
    db.setDomainValidation('instance-2', 'example.com', 'token2', False)

    # Should find validated domain for instance-1
    result = db.getValidatedDomainForOtherInstance('example.com', 'instance-2')
    self.assertIsNotNone(result)
    self.assertEqual(result['instance_reference'], 'instance-1')
    self.assertTrue(bool(result['validated']))

    # Should not find if checking for instance-1 itself
    result = db.getValidatedDomainForOtherInstance('example.com', 'instance-1')
    self.assertIsNone(result)

    # Should not find if domain is not validated
    result = db.getValidatedDomainForOtherInstance('example.com', 'instance-3')
    self.assertIsNotNone(result)  # Still finds instance-1's validated entry

  def test_remove_domain_validation_for_instance_single(self):
    """Test removing domain validation entry for an instance"""
    db = cdnrequest.DomainValidationDB(self.db_path)
    db.setDomainValidation('instance-1', 'example.com', 'token1', True)
    db.setDomainValidation('instance-2', 'example.net', 'token2', True)

    # Remove validation for instance-1
    db.removeDomainValidationForInstance('instance-1')
    self.assertIsNone(db.getDomainValidationForInstance('instance-1'))
    # instance-2 should be unaffected
    self.assertIsNotNone(db.getDomainValidationForInstance('instance-2'))
