import unittest
import mock
from slapos.recipe import cdnrequest
import dns.resolver
from testfixtures import LogCapture
import os
import tempfile
import json
import hashlib
import time
from slapos.recipe.localinstancedb import HostedInstanceLocalDB

class TestCDNRequestFullScenario(unittest.TestCase):
  def setUp(self):
    self.domainvalidation_db_fd, self.domainvalidation_db_path = tempfile.mkstemp()
    self.instance_db_fd, self.instance_db_path = tempfile.mkstemp()
    self.requestinstance_db_fd, self.requestinstance_db_path = tempfile.mkstemp()

    self.buildout = {
      "buildout": {},
      "slap-connection": {
        "computer-id": "test-computer",
        "partition-id": "test-partition",
        "server-url": "http://test.example.com",
        "requested": "started"
      }
    }
    self.options = {
      'domainvalidation-db-path': self.domainvalidation_db_path,
      'instance-db-path': self.instance_db_path,
      'requestinstance-db-path': self.requestinstance_db_path,
      'server-url': 'http://test.example.com',
      'computer-id': 'test-computer',
      'partition-id': 'test-partition',
      'software-url': 'http://test.example.com/software',
      'software-type': 'default',
      'verification-secret': 'test-secret',
      'openssl-binary': 'openssl'  # Will be mocked in tests that need it
    }

  def tearDown(self):
    os.close(self.domainvalidation_db_fd)
    if os.path.exists(self.domainvalidation_db_path):
      os.unlink(self.domainvalidation_db_path)
    os.close(self.instance_db_fd)
    if os.path.exists(self.instance_db_path):
      os.unlink(self.instance_db_path)
    os.close(self.requestinstance_db_fd)
    if os.path.exists(self.requestinstance_db_path):
      os.unlink(self.requestinstance_db_path)

  def test_install_full_scenario(self):
    self._test_full_scenario('install')

  def test_update_full_scenario(self):
    self._test_full_scenario('update')

  def _test_full_scenario(self, method_id):
    """Test full install() scenario with multiple instance states"""

    # Setup instance-db (update list from master)
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    # Setup requestinstance-db (stored instances)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)
    # Setup domainvalidation-db
    domainvalidation_db = cdnrequest.DomainValidationDB(self.domainvalidation_db_path)

    # 1. New instance (not in requestinstance-db)
    new_instance_params = {'custom_domain': 'new.example.com', 'url': 'http://new.example.com'}
    new_instance_data = {'reference': 'new-instance', 'parameters': new_instance_params}
    # Hash calculation matches InstanceListComparator
    new_instance_hash = hashlib.sha256(
      json.dumps(new_instance_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'new-instance',
      json.dumps(new_instance_params, sort_keys=True),
      '{}',
      new_instance_hash,
      str(int(time.time())),
      True  # valid
    )])

    # 2. Invalid instance with no changes (in both DBs, invalid, same hash)
    invalid_no_change_params = {'custom_domain': 'invalid.example.com', 'url': 'http://invalid.example.com'}
    invalid_no_change_data = {'reference': 'invalid-no-change', 'parameters': invalid_no_change_params}
    invalid_no_change_hash = hashlib.sha256(
      json.dumps(invalid_no_change_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'invalid-no-change',
      json.dumps(invalid_no_change_params, sort_keys=True),
      '{}',
      invalid_no_change_hash,
      str(int(time.time())),
      False  # invalid
    )])
    requestinstance_db.insertInstanceList([(
      'invalid-no-change',
      json.dumps(invalid_no_change_params, sort_keys=True),
      '{}',
      invalid_no_change_hash,
      str(int(time.time())),
      False  # invalid
    )])

    # 3. Valid instance with no changes (in both DBs, valid, same hash, already validated)
    valid_no_change_params = {'custom_domain': 'valid.example.com', 'url': 'http://valid.example.com'}
    valid_no_change_data = {'reference': 'valid-no-change', 'parameters': valid_no_change_params, 'valid': True}
    valid_no_change_hash = hashlib.sha256(
      json.dumps(valid_no_change_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'valid-no-change',
      json.dumps(valid_no_change_params, sort_keys=True),
      '{}',
      valid_no_change_hash,
      str(int(time.time())),
      True  # valid
    )])
    # Valid instance with no changes (already stored)
    requestinstance_db.insertInstanceList([(
      'valid-no-change',
      json.dumps(valid_no_change_params, sort_keys=True),
      '{}',
      valid_no_change_hash,
      str(int(time.time())),
      True  # valid
    )])

    # 4. Valid instance with parameter changes but same custom_domain
    valid_changed_params = {'custom_domain': 'changed.example.com', 'url': 'http://changed.example.com', 'new_param': 'new_value'}
    valid_changed_data = {'reference': 'valid-changed', 'parameters': valid_changed_params}
    valid_changed_hash = hashlib.sha256(
      json.dumps(valid_changed_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'valid-changed',
      json.dumps(valid_changed_params, sort_keys=True),
      '{}',
      valid_changed_hash,
      str(int(time.time())),
      True  # valid
    )])
    old_params = {'custom_domain': 'changed.example.com', 'url': 'http://changed.example.com'}
    old_data = {'reference': 'valid-changed', 'parameters': old_params}
    old_hash = hashlib.sha256(
      json.dumps(old_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'valid-changed',
      json.dumps(old_params, sort_keys=True),
      '{}',
      old_hash,
      str(int(time.time())),
      True  # valid
    )])

    # 5. Instance to be removed (in requestinstance-db but not in instance-db)
    to_remove_params = {'custom_domain': 'remove.example.com', 'url': 'http://remove.example.com'}
    to_remove_data = {'reference': 'to-remove', 'parameters': to_remove_params}
    to_remove_hash = hashlib.sha256(
      json.dumps(to_remove_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'to-remove',
      json.dumps(to_remove_params, sort_keys=True),
      '{}',
      to_remove_hash,
      str(int(time.time())),
      True  # valid
    )])

    # 6. Valid instance with DNS validation pending - DNS will pass
    dns_pass_params = {'custom_domain': 'dnspass.example.com', 'url': 'http://dnspass.example.com'}
    dns_pass_data = {'reference': 'dns-pass', 'parameters': dns_pass_params}
    dns_pass_hash = hashlib.sha256(
      json.dumps(dns_pass_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'dns-pass',
      json.dumps(dns_pass_params, sort_keys=True),
      '{}',
      dns_pass_hash,
      str(int(time.time())),
      True  # valid
    )])
    # Already in requestinstance-db but not validated yet
    requestinstance_db.insertInstanceList([(
      'dns-pass',
      json.dumps(dns_pass_params, sort_keys=True),
      '{}',
      dns_pass_hash,
      str(int(time.time())),
      True  # valid
    )])
    # No domain validation entry yet (will be created and validated)

    # 7. Valid instance with DNS validation pending - DNS will fail
    dns_fail_params = {'custom_domain': 'dnsfail.example.com', 'url': 'http://dnsfail.example.com'}
    dns_fail_data = {'reference': 'dns-fail', 'parameters': dns_fail_params}
    dns_fail_hash = hashlib.sha256(
      json.dumps(dns_fail_data, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'dns-fail',
      json.dumps(dns_fail_params, sort_keys=True),
      '{}',
      dns_fail_hash,
      str(int(time.time())),
      True  # valid
    )])
    # Already in requestinstance-db but not validated yet
    requestinstance_db.insertInstanceList([(
      'dns-fail',
      json.dumps(dns_fail_params, sort_keys=True),
      '{}',
      dns_fail_hash,
      str(int(time.time())),
      True  # valid
    )])
    # No domain validation entry yet (will be created but validation will fail)

    # Pre-validate valid-no-change instance
    domainvalidation_db.setDomainValidation('valid-no-change', 'valid.example.com', 'valid-token', True)
    # Pre-validate valid-changed instance (same domain, will be reused)
    domainvalidation_db.setDomainValidation('valid-changed', 'changed.example.com', 'changed-token', True)
    # Pre-validate to-remove instance (will be removed)
    domainvalidation_db.setDomainValidation('to-remove', 'remove.example.com', 'remove-token', True)

    # Mock RequestRecipe and DNS resolver
    with mock.patch('slapos.recipe.request.slapmodule.slap') as mock_slap:
      with mock.patch('dns.resolver.Resolver') as MockResolver:
        # Mock slap library for connection publishing (used by _publishConnectionParameters)
        with mock.patch('slapos.recipe.requestinstancelist.slap') as mock_slap_publish:
          # Setup slap mock for RequestRecipe
          slap_instance = mock.MagicMock()
          request_instance = mock.MagicMock()
          register_instance = mock.MagicMock()
          requested_instance = mock.MagicMock()
          request_instance.return_value = requested_instance
          register_instance.request = request_instance
          slap_instance.registerComputerPartition.return_value = register_instance
          mock_slap.return_value = slap_instance

          # Setup slap mock for connection publishing
          slap_publish_instance = mock.MagicMock()
          computer_partition = mock.MagicMock()
          setConnectionDict = mock.MagicMock()
          computer_partition.setConnectionDict = setConnectionDict
          slap_publish_instance.registerComputerPartition.return_value = computer_partition
          mock_slap_publish.slap.return_value = slap_publish_instance

          # Clear connection cache before test
          from slapos.recipe.librecipe.genericslap import CONNECTION_CACHE
          CONNECTION_CACHE.clear()

          # Setup DNS resolver mock
          mock_resolver_instance = MockResolver.return_value
        mock_answer = mock.MagicMock()
        mock_rdata = mock.MagicMock()

        # Store database path for DNS mock to access
        domainvalidation_db_path = self.options['domainvalidation-db-path']
        # Will be set after recipe is created
        recipe_db_instance = [None]

        def get_dns_response(*args, **kwargs):
          # Get token from database for the domain being checked
          challenge_domain = args[0]
          # Extract domain from challenge domain (e.g., '_slapos-challenge.example.com' -> 'example.com')
          if challenge_domain.startswith('_slapos-challenge.'):
            domain = challenge_domain[len('_slapos-challenge.'):]
          else:
            # Handle custom dns-entry-name
            parts = challenge_domain.split('.', 1)
            domain = parts[1] if len(parts) > 1 else challenge_domain

          # Handle DNS validation:
          # - new.example.com: DNS validation will wait (fail initially)
          # - dnsfail.example.com: DNS will fail - return wrong token
          # - dns-pass.example.com: DNS will pass
          if domain == 'new.example.com' or domain == 'dnsfail.example.com':
            # DNS will fail - return wrong token
            mock_rdata.strings = [b'wrong-token']
          else:
            # For all other domains, try to get token from database
            # Use recipe's database instance if available, otherwise create a new connection
            db_to_use = recipe_db_instance[0]
            if db_to_use is None:
              db_to_use = cdnrequest.DomainValidationDB(domainvalidation_db_path)

            # Try to get token by domain (most reliable since token is stored with domain)
            all_entries = db_to_use.fetchAll(
              "SELECT * FROM domain_validation WHERE domain=?", (domain,)
            )
            if all_entries:
              mock_rdata.strings = [all_entries[0]['token'].encode('utf-8')]
            else:
              # If not found by domain, try by instance reference
              found = False
              for instance_ref in ['new-instance', 'invalid-no-change', 'valid-changed', 'dns-pass']:
                db_entry = db_to_use.getDomainValidationForInstance(instance_ref)
                if db_entry and db_entry['domain'] == domain:
                  mock_rdata.strings = [db_entry['token'].encode('utf-8')]
                  found = True
                  break

              if not found:
                # Token not created yet, return placeholder
                mock_rdata.strings = [b'placeholder']

          mock_answer.__iter__.return_value = iter([mock_rdata])
          return mock_answer

          mock_resolver_instance.resolve.side_effect = get_dns_response

          # Create recipe and call install()
          recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)
          # Store recipe's database instance for DNS mock to use
          recipe_db_instance[0] = recipe.domain_validation_db

          with LogCapture() as log:
            result = getattr(recipe, method_id)()

          # Verify results
          # 1. New instance should NOT be requested (DNS validation will wait)
          self.assertNotIn('new-instance', recipe.request_instances)
          # Verify it was added to requestinstance-db but marked as invalid
          stored = requestinstance_db.getInstance('new-instance')
          self.assertIsNotNone(stored)
          self.assertEqual(stored['reference'], 'new-instance')
          self.assertFalse(bool(stored['valid_parameter']))  # Should be invalid due to DNS failure
          # Verify domain validation for new instance (created but not validated)
          db_entry = domainvalidation_db.getDomainValidationForInstance('new-instance')
          self.assertIsNotNone(db_entry)
          self.assertEqual(db_entry['domain'], 'new.example.com')
          self.assertFalse(bool(db_entry['validated']))  # DNS validation failed

          # 2. Invalid instance with no changes should be re-validated (but not requested)
          # Check that it's still in the database and still invalid
          stored = requestinstance_db.getInstance('invalid-no-change')
          self.assertIsNotNone(stored)
          self.assertFalse(bool(stored['valid_parameter']))
          # Should not be in request_instances (validation failed)
          self.assertNotIn('invalid-no-change', recipe.request_instances)

          # 3. Valid instance with no changes should not be requested (already validated, no changes)
          # Should not be in request_instances
          self.assertNotIn('valid-no-change', recipe.request_instances)
          # Should still be in database
          stored = requestinstance_db.getInstance('valid-no-change')
          self.assertIsNotNone(stored)
          # Domain validation should still exist
          db_entry = domainvalidation_db.getDomainValidationForInstance('valid-no-change')
          self.assertIsNotNone(db_entry)
          self.assertTrue(bool(db_entry['validated']))

          # 4. Valid instance with changes should be requested
          self.assertIn('valid-changed', recipe.request_instances)
          # Domain validation should still be valid (same domain)
          db_entry = domainvalidation_db.getDomainValidationForInstance('valid-changed')
          self.assertIsNotNone(db_entry)
          self.assertEqual(db_entry['domain'], 'changed.example.com')
          self.assertTrue(bool(db_entry['validated']))
          # Verify it was updated in requestinstance-db
          stored = requestinstance_db.getInstance('valid-changed')
          self.assertIsNotNone(stored)
          stored_params = json.loads(stored['json_parameters'])
          self.assertEqual(stored_params['new_param'], 'new_value')

          # 5. Instance to be removed should be destroyed
          stored = requestinstance_db.getInstance('to-remove')
          self.assertIsNone(stored)
          # Domain validation should be removed
          db_entry = domainvalidation_db.getDomainValidationForInstance('to-remove')
          self.assertIsNone(db_entry)

          # 6. Valid instance with DNS validation pending - DNS will pass
          # Should be requested after DNS validation passes
          self.assertIn('dns-pass', recipe.request_instances)
          # Verify it was updated in requestinstance-db
          stored = requestinstance_db.getInstance('dns-pass')
          self.assertIsNotNone(stored)
          self.assertTrue(bool(stored['valid_parameter']))
          # Verify domain validation was created and validated
          db_entry = domainvalidation_db.getDomainValidationForInstance('dns-pass')
          self.assertIsNotNone(db_entry)
          self.assertEqual(db_entry['domain'], 'dnspass.example.com')
          self.assertTrue(bool(db_entry['validated']))

          # 7. Valid instance with DNS validation pending - DNS will fail
          # Should NOT be requested (DNS validation failed)
          self.assertNotIn('dns-fail', recipe.request_instances)
          # Verify it's still in requestinstance-db but invalid
          stored = requestinstance_db.getInstance('dns-fail')
          self.assertIsNotNone(stored)
          self.assertFalse(bool(stored['valid_parameter']))
          # Verify domain validation was created but not validated
          db_entry = domainvalidation_db.getDomainValidationForInstance('dns-fail')
          self.assertIsNotNone(db_entry)
          self.assertEqual(db_entry['domain'], 'dnsfail.example.com')
          self.assertFalse(bool(db_entry['validated']))

          # Verify request_instance was called for modified instances only
          # valid-changed (modified) + dns-pass (DNS validation passed)
          # + destroyed instance (to-remove) = 3 calls
          # Note: new-instance is not requested because DNS validation fails
          # Note: valid-no-change is not requested because it's unchanged
          self.assertEqual(request_instance.call_count, 3)

          # Verify published connection parameters for each instance
          # Connection parameters are published via setConnectionDict with slave_reference

          # Helper to extract published params for an instance from setConnectionDict calls
          def get_published_params(instance_ref):
            for call in setConnectionDict.call_args_list:
              # call[0] is tuple of positional args, call[1] is dict of keyword args
              if len(call[0]) > 0:
                conn_params = call[0][0]
                slave_ref = call[1].get('slave_reference')
                if slave_ref == instance_ref:
                  return conn_params
            return None

          # 1. new-instance: DNS validation failed - should publish DNS challenge info
          new_published = get_published_params('new-instance')
          self.assertIsNotNone(new_published, "new-instance should have published connection parameters")
          self.assertIn('txt_record', new_published)
          self.assertIn('txt_value', new_published)
          self.assertIn('message', new_published)
          self.assertEqual(new_published['txt_record'], '_slapos-challenge.new.example.com')
          # Verify token is present (should be generated)
          self.assertIsNotNone(new_published['txt_value'])
          self.assertNotEqual(new_published['txt_value'], '')
          # Verify message content
          expected_message = (
            'Custom domain verification failed. '
            'Please add TXT record "%s" with value "%s".'
            % (new_published['txt_record'], new_published['txt_value'])
          )
          self.assertEqual(new_published['message'], expected_message)

          # 2. invalid-no-change: Validation failed - should publish DNS challenge info
          # Note: invalid-no-change has custom_domain but is marked invalid in DB
          # It will go through validateInstance, and DNS will fail (wrong token)
          # So it should publish DNS challenge info, not just error message
          invalid_published = get_published_params('invalid-no-change')
          self.assertIsNotNone(invalid_published, "invalid-no-change should have published connection parameters")
          # Since it has custom_domain, DNS validation will be attempted and fail
          # So it should have DNS challenge info
          self.assertIn('txt_record', invalid_published)
          self.assertIn('txt_value', invalid_published)
          self.assertIn('message', invalid_published)
          self.assertEqual(invalid_published['txt_record'], '_slapos-challenge.invalid.example.com')
          # Verify token is present (should be generated)
          self.assertIsNotNone(invalid_published['txt_value'])
          self.assertNotEqual(invalid_published['txt_value'], '')
          # Verify message content
          expected_message = (
            'Custom domain verification failed. '
            'Please add TXT record "%s" with value "%s".'
            % (invalid_published['txt_record'], invalid_published['txt_value'])
          )
          self.assertEqual(invalid_published['message'], expected_message)

          # 3. valid-no-change: Already validated, no changes - should not publish
          # (no connection params returned from validateInstance, and no request_conn_params)
          valid_no_change_published = get_published_params('valid-no-change')
          self.assertIsNone(valid_no_change_published, "valid-no-change should not have published connection parameters")

          # 4. valid-changed: Modified and validated - should publish success message
          valid_changed_published = get_published_params('valid-changed')
          self.assertIsNotNone(valid_changed_published, "valid-changed should have published connection parameters")
          self.assertIn('message', valid_changed_published)
          self.assertEqual(valid_changed_published['message'], 'Your instance is valid the request has been transmitted to the master')

          # 5. to-remove: Destroyed - should not publish (instance is removed, no publishing in _processDestroyedInstance)
          to_remove_published = get_published_params('to-remove')
          self.assertIsNone(to_remove_published, "to-remove should not have published connection parameters")

          # 6. dns-pass: DNS validation passed - should publish success message
          dns_pass_published = get_published_params('dns-pass')
          self.assertIsNotNone(dns_pass_published, "dns-pass should have published connection parameters")
          self.assertIn('message', dns_pass_published)
          self.assertEqual(dns_pass_published['message'], 'Your instance is valid the request has been transmitted to the master')

          # 7. dns-fail: DNS validation failed - should publish DNS challenge info
          dns_fail_published = get_published_params('dns-fail')
          self.assertIsNotNone(dns_fail_published, "dns-fail should have published connection parameters")
          self.assertIn('txt_record', dns_fail_published)
          self.assertIn('txt_value', dns_fail_published)
          self.assertIn('message', dns_fail_published)
          self.assertEqual(dns_fail_published['txt_record'], '_slapos-challenge.dnsfail.example.com')
          # Verify token is present (should be generated)
          self.assertIsNotNone(dns_fail_published['txt_value'])
          self.assertNotEqual(dns_fail_published['txt_value'], '')
          # Verify message content
          expected_message = (
            'Custom domain verification failed. '
            'Please add TXT record "%s" with value "%s".'
            % (dns_fail_published['txt_record'], dns_fail_published['txt_value'])
          )
          self.assertEqual(dns_fail_published['message'], expected_message)


class TestCDNRequestRecipe(unittest.TestCase):

  def setUp(self):
    self.domainvalidation_db_fd, self.domainvalidation_db_path = tempfile.mkstemp()

    self.buildout = {
      "buildout": {},
    }
    self.options = {
      'instance-db-path': "/path/to/instance.db",
      'domainvalidation-db-path': self.domainvalidation_db_path,
      'requestinstance-db-path': "/path/to/requestinstance.db",
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
    self.assertIn('Your domain "example.com" can not be validated. Please contact support.', error_list[0])
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

  def test_validate_server_alias_requires_custom_domain(self):
    """Test validation fails when server-alias is provided without custom_domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # server-alias without custom_domain should fail
    parameters = {
      'server-alias': 'example.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn('server-alias requires custom_domain to be set', error_list)

  def test_validate_server_alias_invalid_domain(self):
    """Test validation fails for invalid server-alias domains"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Invalid domain in server-alias
    parameters = {
      'server-alias': 'invalid..domain.com valid.domain.com',
      'custom_domain': 'domain.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn("server-alias 'invalid..domain.com' not valid", error_list)


  @mock.patch('dns.resolver.Resolver')
  def test_validate_server_alias_same_root_domain(self, MockResolver):
    """Test validation accepts server-alias with same root domain as custom_domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DNS to return success
    mock_resolver_instance = MockResolver.return_value
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

    # server-alias with same root domain as custom_domain should be valid
    parameters = {
      'custom_domain': 'example.com',
      'server-alias': 'www.example.com api.example.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

  def test_validate_server_alias_different_root_domain(self):
    """Test validation fails for server-alias with different root domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # server-alias with different root domain should fail
    parameters = {
      'custom_domain': 'example.com',
      'server-alias': 'otherdomain.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn("server-alias 'otherdomain.com' must be part of the same root domain as custom_domain (example.com)", error_list)

  @mock.patch('dns.resolver.Resolver')
  def test_validate_server_alias_wildcard_same_root_domain(self, MockResolver):
    """Test validation accepts wildcard server-alias with same root domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DNS to return success
    mock_resolver_instance = MockResolver.return_value
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

    # Wildcard server-alias with same root domain should be valid
    parameters = {
      'custom_domain': 'example.com',
      'server-alias': '*.example.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

  def test_validate_server_alias_wildcard_different_root_domain(self):
    """Test validation fails for wildcard server-alias with different root domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Wildcard server-alias with different root domain should fail
    parameters = {
      'custom_domain': 'example.com',
      'server-alias': '*.otherdomain.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn("server-alias '*.otherdomain.com' must be part of the same root domain as custom_domain (example.com)", error_list)

  @mock.patch('dns.resolver.Resolver')
  def test_validate_server_alias_matches_custom_domain(self, MockResolver):
    """Test validation accepts server-alias that matches custom_domain exactly"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DNS to return success
    mock_resolver_instance = MockResolver.return_value
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

    # server-alias matching custom_domain exactly should be valid
    parameters = {
      'custom_domain': 'example.com',
      'server-alias': 'example.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

  @mock.patch('dns.resolver.Resolver')
  def test_validate_server_alias_subdomain_of_custom_domain(self, MockResolver):
    """Test validation accepts server-alias that is subdomain of custom_domain"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DNS to return success
    mock_resolver_instance = MockResolver.return_value
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

    # server-alias as subdomain of custom_domain should be valid
    parameters = {
      'custom_domain': 'www.example.com',
      'server-alias': 'api.example.com'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

  @mock.patch('dns.resolver.Resolver')
  def test_validate_server_alias_update_adds_new_hosts(self, MockResolver):
    """Test that updating server-alias for already validated instance adds new hosts to used_hosts"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Mock DNS to return success
    mock_resolver_instance = MockResolver.return_value
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

    # Step 1: Create instance with initial server-alias and validate it
    initial_params = {
      'custom_domain': 'example.com',
      'server-alias': 'www.example.com'
    }

    # Pre-populate requestinstance_db to simulate existing validated instance
    recipe.requestinstance_db.insertInstanceList([(
      'ref1',
      json.dumps(initial_params, sort_keys=True),
      "{}",
      'initial-hash',
      "1234567890",
      True
    )])

    # Pre-populate domain_validation_db to simulate already validated domain
    recipe.domain_validation_db.setDomainValidation('ref1', 'example.com', 'test-token', True)

    # Pre-populate used_hosts with initial hosts
    recipe.domain_validation_db.addUsedHosts('ref1', {'example.com', 'www.example.com'})

    # Verify initial hosts are in used_hosts
    hosts_before = recipe.domain_validation_db.fetchAll(
      "SELECT host FROM used_hosts WHERE instance_reference=?",
      ('ref1',)
    )
    hosts_before_set = {row['host'] for row in hosts_before}
    self.assertEqual(hosts_before_set, {'example.com', 'www.example.com'})

    # Step 2: Update server-alias with new aliases
    updated_params = {
      'custom_domain': 'example.com',
      'server-alias': 'www.example.com api.example.com blog.example.com'
    }

    # Validate the updated instance (should pass DNS since domain is already validated)
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', updated_params)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

    # Step 3: Verify new hosts are added to used_hosts
    # Note: The hosts are added in validateInstance when DNS validation passes
    # Since the domain is already validated, validateInstance will return early
    # and add the hosts. Let's check the used_hosts table
    hosts_after = recipe.domain_validation_db.fetchAll(
      "SELECT host FROM used_hosts WHERE instance_reference=?",
      ('ref1',)
    )
    hosts_after_set = {row['host'] for row in hosts_after}
    # Should include custom_domain and all server-alias entries
    expected_hosts = {'example.com', 'www.example.com', 'api.example.com', 'blog.example.com'}
    self.assertEqual(hosts_after_set, expected_hosts)

  def test_validate_url_netloc_list_invalid(self):
    """Test validation fails for invalid url-netloc-list"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Invalid netloc format
    parameters = {
      'url-netloc-list': 'invalid-netloc example.com:80'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn("slave url-netloc-list 'invalid-netloc' invalid", error_list)

  def test_validate_url_netloc_list_valid(self):
    """Test validation accepts valid url-netloc-list"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Valid netloc format
    parameters = {
      'url-netloc-list': 'example.com:80 backend.example.com:443'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

  def test_validate_cipher_valid(self):
    """Test validation accepts valid ciphers"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Valid cipher from GOOD_CIPHER_LIST
    parameters = {
      'ciphers': 'ECDHE-RSA-AES256-GCM-SHA384 ECDHE-ECDSA-AES128-GCM-SHA256'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])

  def test_validate_cipher_invalid(self):
    """Test validation fails for invalid ciphers"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Invalid cipher
    parameters = {
      'ciphers': 'INVALID-CIPHER-SUITE'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn("Cipher 'INVALID-CIPHER-SUITE' is not supported.", error_list)

  def test_validate_cipher_translatable(self):
    """Test validation accepts translatable ciphers and logs warning"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # Translatable cipher (old format)
    parameters = {
      'ciphers': 'ECDHE-RSA-AES256-CBC-SHA'
    }
    with LogCapture() as log:
      is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertTrue(is_valid)
    self.assertEqual(error_list, [])
    # Check that warning was logged
    log.check(
      ('test', 'WARNING', "Instance ref1: Cipher 'ECDHE-RSA-AES256-CBC-SHA' translated to 'ECDHE-RSA-AES256-SHA'"),
    )

  def test_validate_ssl_certificate_valid(self):
    """Test validation accepts valid SSL certificates"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', {
      **self.options,
      'openssl-binary': '/usr/bin/openssl'
    })

    valid_cert = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL2Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z
-----END CERTIFICATE-----"""

    parameters = {
      'ssl_proxy_ca_crt': valid_cert
    }

    # Mock openssl subprocess call to return success
    with mock.patch('subprocess.Popen') as mock_popen:
      mock_process = mock.MagicMock()
      mock_process.returncode = 0
      mock_process.communicate.return_value = (b'', b'')
      mock_popen.return_value = mock_process

      is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
      # Should pass validation (openssl returns success)
      self.assertTrue(is_valid)
      self.assertEqual(error_list, [])

  def test_validate_ssl_certificate_invalid(self):
    """Test validation fails for invalid SSL certificates"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', {
      **self.options,
      'openssl-binary': '/usr/bin/openssl'
    })

    # Invalid certificate content
    invalid_cert = "not a valid certificate"
    parameters = {
      'ssl_proxy_ca_crt': invalid_cert
    }

    # Mock openssl to return error
    with mock.patch('subprocess.Popen') as mock_popen:
      mock_process = mock.MagicMock()
      mock_process.returncode = 1  # openssl error
      mock_process.communicate.return_value = (b'error', b'')
      mock_popen.return_value = mock_process

      is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
      self.assertFalse(is_valid)
      self.assertIn('ssl_proxy_ca_crt is invalid', error_list)

  def test_validate_ssl_key_cert_match(self):
    """Test validation checks SSL key and certificate match"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', {
      **self.options,
      'openssl-binary': '/usr/bin/openssl'
    })

    # Mock matching moduli (key and cert match)
    matching_modulus = b'Modulus=ABCD1234\n'
    parameters = {
      'ssl_key': '-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----',
      'ssl_crt': '-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----'
    }

    with mock.patch('subprocess.Popen') as mock_popen:
      # First call (key modulus)
      mock_key_process = mock.MagicMock()
      mock_key_process.returncode = 0
      mock_key_process.communicate.return_value = (matching_modulus, b'')

      # Second call (cert modulus)
      mock_cert_process = mock.MagicMock()
      mock_cert_process.returncode = 0
      mock_cert_process.communicate.return_value = (matching_modulus, b'')

      mock_popen.side_effect = [mock_key_process, mock_cert_process]

      is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
      self.assertTrue(is_valid)
      self.assertEqual(error_list, [])

  def test_validate_ssl_key_cert_mismatch(self):
    """Test validation fails when SSL key and certificate don't match"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', {
      **self.options,
      'openssl-binary': '/usr/bin/openssl'
    })

    parameters = {
      'ssl_key': '-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----',
      'ssl_crt': '-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----'
    }

    with mock.patch('subprocess.Popen') as mock_popen:
      # First call (key modulus)
      mock_key_process = mock.MagicMock()
      mock_key_process.returncode = 0
      mock_key_process.communicate.return_value = (b'Modulus=KEY123\n', b'')

      # Second call (cert modulus)
      mock_cert_process = mock.MagicMock()
      mock_cert_process.returncode = 0
      mock_cert_process.communicate.return_value = (b'Modulus=CERT456\n', b'')

      mock_popen.side_effect = [mock_key_process, mock_cert_process]

      is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
      self.assertFalse(is_valid)
      self.assertIn('slave ssl_key and ssl_crt does not match', error_list)

  def test_validate_ssl_ca_crt_requires_key_and_cert(self):
    """Test validation requires ssl_crt and ssl_key when ssl_ca_crt is present"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # ssl_ca_crt without ssl_crt and ssl_key
    parameters = {
      'ssl_ca_crt': '-----BEGIN CERTIFICATE-----\ntest ca\n-----END CERTIFICATE-----'
    }
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    self.assertFalse(is_valid)
    self.assertIn('ssl_ca_crt is present, so ssl_crt and ssl_key are required', error_list)

  def test_validate_ssl_ca_crt_with_key_and_cert(self):
    """Test validation passes when ssl_ca_crt has both ssl_crt and ssl_key"""
    recipe = cdnrequest.CDNRequestRecipe(self.buildout, 'test', self.options)

    # ssl_ca_crt with ssl_crt and ssl_key
    parameters = {
      'ssl_ca_crt': '-----BEGIN CERTIFICATE-----\ntest ca\n-----END CERTIFICATE-----',
      'ssl_crt': '-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----',
      'ssl_key': '-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----'
    }
    # Should pass basic validation (SSL matching would require openssl)
    is_valid, error_list, conn_params = recipe.validateInstance('ref1', parameters)
    # Will fail SSL matching if openssl is not available, but that's expected
    # The important part is it doesn't fail on the ssl_ca_crt requirement check
    if 'openssl-binary' not in self.options:
      # Without openssl, SSL matching is skipped, so it should pass
      self.assertTrue(is_valid)


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
