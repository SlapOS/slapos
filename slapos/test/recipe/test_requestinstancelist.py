import json
import mock
import os
import tempfile
import unittest
from collections import defaultdict

from slapos.recipe import requestinstancelist
from slapos.recipe.localinstancedb import HostedInstanceLocalDB
from testfixtures import LogCapture


class TestRequestInstanceList(unittest.TestCase):

  def setUp(self):
    # Create temporary databases
    self.instance_db_fd, self.instance_db_path = tempfile.mkstemp()
    self.requestinstance_db_fd, self.requestinstance_db_path = tempfile.mkstemp()

    # Setup buildout
    self.buildout = {
      "buildout": {},
      "slap-connection": {
        "computer-id": "test-computer",
        "partition-id": "test-partition",
        "server-url": "http://test.example.com",
        "requested": "started"
      }
    }

    # Mock slap module (RequestRecipe uses it from request module)
    slap_patch = mock.patch(
      "slapos.recipe.request.slapmodule.slap", autospec=True)
    slap = slap_patch.start()
    self.addCleanup(slap_patch.stop)

    slap_instance = mock.MagicMock()
    self.request_instance = mock.MagicMock()
    register_instance = mock.MagicMock()
    self.requested_instance = mock.MagicMock()
    self.request_instance.return_value = self.requested_instance
    register_instance.request = self.request_instance
    slap_instance.registerComputerPartition.return_value = register_instance
    slap.return_value = slap_instance

    # Mock getConnectionParameter
    self.instance_getConnectionParameter = \
        self.requested_instance.getConnectionParameter

    # Mock slap library for connection publishing (used by _publishConnectionParameters)
    slap_publish_patch = mock.patch('slapos.recipe.requestinstancelist.slap')
    self.slap_publish_lib = slap_publish_patch.start()
    self.addCleanup(slap_publish_patch.stop)

    # Setup mock computer partition for publishing
    self.computer_partition = mock.MagicMock()
    self.setConnectionDict = mock.MagicMock()
    self.computer_partition.setConnectionDict = self.setConnectionDict

    # Setup mock slap instance for publishing
    self.slap_instance_publish = mock.MagicMock()
    self.slap_instance_publish.registerComputerPartition.return_value = self.computer_partition

    # Setup mock slap class
    self.slap_class = mock.MagicMock()
    self.slap_class.return_value = self.slap_instance_publish
    self.slap_publish_lib.slap = self.slap_class

    # Clear connection cache before each test
    from slapos.recipe.librecipe.genericslap import CONNECTION_CACHE
    CONNECTION_CACHE.clear()

    # Default options
    self.options = {
      'instance-db-path': self.instance_db_path,
      'requestinstance-db-path': self.requestinstance_db_path,
      'server-url': 'http://test.example.com',
      'computer-id': 'test-computer',
      'partition-id': 'test-partition',
      'software-url': 'http://test.example.com/software',
      'software-type': 'default',
      'shared': 'false',
    }

  def tearDown(self):
    os.close(self.instance_db_fd)
    os.unlink(self.instance_db_path)
    os.close(self.requestinstance_db_fd)
    os.unlink(self.requestinstance_db_path)

  def _createInstanceDB(self, instances, connection_params=None):
    """Helper to populate instance database

    Args:
      instances: List of tuples (ref, params, valid)
      connection_params: Optional dict mapping instance ref to error info dict
    """
    db = HostedInstanceLocalDB(self.instance_db_path)
    instance_list = []
    for ref, params, valid in instances:
      params_json = json.dumps(params, sort_keys=True)
      # Create a simple hash for testing
      import hashlib
      instance_hash = hashlib.sha256(
        json.dumps({'reference': ref, 'parameters': params}, sort_keys=True).encode('utf-8')
      ).hexdigest()
      # Use error info if provided, otherwise empty dict
      if connection_params and ref in connection_params:
        error_json = json.dumps(connection_params[ref], sort_keys=True)
      elif not valid:
        error_json = "{}"  # Invalid but no error info provided
      else:
        error_json = "{}"  # Valid instances have empty error
      instance_list.append((
        ref,
        params_json,
        error_json,
        instance_hash,
        "1234567890",
        valid
      ))
    db.insertInstanceList(instance_list)

  def _getRequestInstanceDB(self):
    """Helper to get request instance database contents"""
    db = HostedInstanceLocalDB(self.requestinstance_db_path)
    return db.getInstanceList("reference, json_parameters, json_error, valid_parameter")

  def test_new_valid_instance(self):
    """Test requesting a new valid instance"""
    # Setup: one instance in instance-db, none in requestinstance-db
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Connection parameters are not extracted since 'return' is not a recipe option
    # So we don't need to mock getConnectionParameter

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify instance was requested
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][2], 'instance1')  # name parameter

    # Verify instance was added to requestinstance-db
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')
    stored_params = json.loads(stored[0]['json_parameters'])
    self.assertEqual(stored_params['key'], 'value')
    # Connection parameters are not extracted since 'return' is not a recipe option
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {})

  def test_new_invalid_instance(self):
    """Test that invalid instances are tracked but not requested"""
    # Setup: one invalid instance in instance-db
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, False)
    ])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )

    with LogCapture() as log:
      recipe.install()

    # Verify instance was NOT requested
    self.request_instance.assert_not_called()

    # Verify instance was still tracked in requestinstance-db
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')
    self.assertEqual(stored[0]['valid_parameter'], False)

    log.check(
      ('test', 'DEBUG', 'Comparison results: 1 added, 0 removed, 0 modified'),
      ('test', 'WARNING', 'Instance instance1 failed validation: Instance validation failed'),
      ('test', 'DEBUG', 'Tracking invalid new instance (not requesting): instance1'),
    )

  def test_modified_valid_instance(self):
    """Test updating a modified valid instance"""
    # Setup: instance exists in both DBs with different parameters
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Add to instance-db with new parameters
    import hashlib
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(new_params, sort_keys=True),
      "{}",
      new_hash,
      "1234567890",
      True
    )])

    # Add to requestinstance-db with old parameters
    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': old_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      '{"param1": "old_conn1"}',
      old_hash,
      "1234567890",
      True
    )])

    # Connection parameters are not extracted since 'return' is not a recipe option
    # So we don't need to mock getConnectionParameter

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify instance was requested (updated)
    self.request_instance.assert_called_once()

    # Verify instance was updated in requestinstance-db
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    stored_params = json.loads(stored[0]['json_parameters'])
    self.assertEqual(stored_params['key'], 'new_value')
    # Error info should be empty for valid instances
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {})

  def test_modified_invalid_instance(self):
    """Test that modified invalid instances are tracked but not requested"""
    # Setup: instance exists in both DBs, but now invalid
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(new_params, sort_keys=True),
      "{}",
      new_hash,
      "1234567890",
      False  # Now invalid
    )])

    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': old_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      '{"param1": "old_conn1"}',
      old_hash,
      "1234567890",
      True
    )])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )

    with LogCapture() as log:
      recipe.install()

    # Verify instance was NOT requested
    self.request_instance.assert_not_called()

    # Verify instance was updated in requestinstance-db (marked as invalid)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], False)
    # Error info should be empty for invalid instances when no errors are provided
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {})

    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 1 modified'),
      ('test', 'WARNING', 'Instance instance1 failed validation: Instance validation failed'),
      ('test', 'DEBUG', 'Tracking invalid modified instance (not requesting): instance1'),
    )

  def test_destroyed_instance(self):
    """Test destroying a removed instance"""
    # Setup: instance exists in requestinstance-db but not in instance-db
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      '{"param1": "conn1"}',
      instance_hash,
      "1234567890",
      True
    )])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify destroy was requested with state='destroyed'
    self.request_instance.assert_called_once()
    call_kwargs = self.request_instance.call_args[1]
    self.assertEqual(call_kwargs['state'], 'destroyed')

    # Verify instance was removed from requestinstance-db
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 0)

  def test_multiple_operations(self):
    """Test multiple operations in one run"""
    # Setup: complex scenario
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib

    # New valid instance
    new_params = {'key': 'new'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'new1', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'new1',
      json.dumps(new_params, sort_keys=True),
      "{}",
      new_hash,
      "1234567890",
      True
    )])

    # Modified instance
    mod_params = {'key': 'modified'}
    mod_hash = hashlib.sha256(
      json.dumps({'reference': 'mod1', 'parameters': mod_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'mod1',
      json.dumps(mod_params, sort_keys=True),
      "{}",
      mod_hash,
      "1234567890",
      True
    )])

    # Old version in requestinstance-db
    old_params = {'key': 'old'}
    old_hash = hashlib.sha256(
      json.dumps({'reference': 'mod1', 'parameters': old_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'mod1',
      json.dumps(old_params, sort_keys=True),
      '{}',
      old_hash,
      "1234567890",
      True
    )])

    # Instance to destroy
    destroy_params = {'key': 'destroy'}
    destroy_hash = hashlib.sha256(
      json.dumps({'reference': 'destroy1', 'parameters': destroy_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'destroy1',
      json.dumps(destroy_params, sort_keys=True),
      '{}',
      destroy_hash,
      "1234567890",
      True
    )])

    self.instance_getConnectionParameter.return_value = 'conn_value'

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify all operations were called
    self.assertEqual(self.request_instance.call_count, 3)  # new, modified, destroy

    # Verify final state of requestinstance-db
    stored = self._getRequestInstanceDB()
    stored_refs = {row['reference'] for row in stored}
    self.assertEqual(stored_refs, {'new1', 'mod1'})  # destroy1 removed
    self.assertNotIn('destroy1', stored_refs)

  def test_incremental_updates(self):
    """Test that database is updated incrementally, allowing resume after failure"""
    # Setup: two new instances
    self._createInstanceDB([
      ('instance1', {'key': 'value1'}, True),
      ('instance2', {'key': 'value2'}, True)
    ])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )

    # First install - both should be processed and saved
    recipe.install()

    # Verify both instances were saved to DB
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 2)
    stored_refs = {row['reference'] for row in stored}
    self.assertEqual(stored_refs, {'instance1', 'instance2'})

    # Now add a third instance and run again
    # Only the new instance should be processed
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    import hashlib
    new_params = {'key': 'value3'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'instance3', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'instance3',
      json.dumps(new_params, sort_keys=True),
      "{}",
      new_hash,
      "1234567890",
      True
    )])

    # Reset call count
    self.request_instance.reset_mock()

    # Run install again - should only process instance3
    recipe.install()

    # Verify instance3 was added
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 3)
    stored_refs = {row['reference'] for row in stored}
    self.assertEqual(stored_refs, {'instance1', 'instance2', 'instance3'})

    # Verify only one request was made (for instance3)
    self.assertEqual(self.request_instance.call_count, 1)

  def test_software_url_from_recipe_options(self):
    """Test that software-url comes from recipe options, not instance parameters"""
    self._createInstanceDB([
      ('instance1', {
        'software-url': 'http://custom.example.com/software',  # Should be ignored
        'key': 'value'
      }, True)
    ])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify software-url from recipe options was used, not from instance parameters
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][0], self.options['software-url'])

  def test_software_type_from_recipe_options(self):
    """Test that software-type comes from recipe options, not instance parameters"""
    self._createInstanceDB([
      ('instance1', {
        'software-type': 'custom-type',  # Should be ignored
        'key': 'value'
      }, True)
    ])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify software-type from recipe options was used, not from instance parameters
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][1], self.options['software-type'])

  def test_config_parameters_extraction(self):
    """Test that all parameters are automatically prefixed with config-"""
    self._createInstanceDB([
      ('instance1', {
        'param1': 'value1',
        'param2': 'value2',
        'other-param': 'value3'
      }, True)
    ])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify request was made with parameters prefixed with config-
    self.request_instance.assert_called_once()
    call_kwargs = self.request_instance.call_args[1]
    partition_params = call_kwargs['partition_parameter_kw']
    # All parameters should be prefixed with config- in the request options
    # The RequestRecipe will strip the 'config-' prefix when creating partition_parameter_kw
    # So we check that the request was made with config-param1, config-param2, etc.
    # But partition_parameter_kw will have param1, param2 (without config- prefix)
    self.assertEqual(partition_params['param1'], 'value1')
    self.assertEqual(partition_params['param2'], 'value2')
    self.assertEqual(partition_params['other-param'], 'value3')

  def test_sla_parameters_from_recipe_options(self):
    """Test that sla-* parameters come from recipe options, not instance parameters"""
    self._createInstanceDB([
      ('instance1', {
        'param1': 'value1',
        'sla-region': 'us-east',  # This should be ignored (sla-* from instance params)
      }, True)
    ])

    # Add sla-* options to recipe options
    options = self.options.copy()
    options['sla-region'] = 'eu-west'
    options['sla-zone'] = 'zone1'

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify request was made with sla-* from recipe options, not instance parameters
    self.request_instance.assert_called_once()
    call_kwargs = self.request_instance.call_args[1]
    filter_kw = call_kwargs['filter_kw']
    self.assertEqual(filter_kw['region'], 'eu-west')
    self.assertEqual(filter_kw['zone'], 'zone1')
    # Verify instance parameter sla-region was prefixed with config- (not used as sla-)
    partition_params = call_kwargs['partition_parameter_kw']
    self.assertEqual(partition_params['sla-region'], 'us-east')  # Prefixed with config-

  def test_missing_software_url_error(self):
    """Test error when software-url is missing"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Remove software-url from options
    options = self.options.copy()
    del options['software-url']

    with self.assertRaises(ValueError) as cm:
      requestinstancelist.Recipe(self.buildout, 'test', options)

    self.assertIn('software-url is required', str(cm.exception))

  def test_missing_software_type_error(self):
    """Test error when software-type is missing"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Remove software-type from options
    options = self.options.copy()
    del options['software-type']

    with self.assertRaises(ValueError) as cm:
      requestinstancelist.Recipe(self.buildout, 'test', options)

    self.assertIn('software-type is required', str(cm.exception))

  def test_no_instances(self):
    """Test behavior when there are no instances"""
    # Empty databases
    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )

    with LogCapture() as log:
      result = recipe.install()

    self.assertEqual(result, [])
    self.request_instance.assert_not_called()

    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 0 modified'),
    )

  def test_shared_instances(self):
    """Test requesting shared instances"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    options = self.options.copy()
    options['shared'] = 'true'

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify shared=True was passed
    self.request_instance.assert_called_once()
    call_kwargs = self.request_instance.call_args[1]
    self.assertTrue(call_kwargs['shared'])

  def test_default_state(self):
    """Test that default state is 'started'"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify default state 'started' was used
    self.request_instance.assert_called_once()
    call_kwargs = self.request_instance.call_args[1]
    self.assertEqual(call_kwargs['state'], 'started')

  def test_request_failure_handling(self):
    """Test that RequestOptional handles failures gracefully"""
    # RequestOptional doesn't raise on failures, so instance should still be tracked
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Make request fail (but RequestOptional won't raise)
    from slapos import slap as slapmodule
    self.request_instance.side_effect = slapmodule.NotFoundError("Not found")

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )

    # Should not raise (RequestOptional handles it)
    with LogCapture() as log:
      recipe.install()

    # Instance should still be tracked in DB (but without connection params)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')
    # Connection parameters are not extracted since 'return' is not a recipe option
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {})

  def test_connection_parameters_preserved_on_update_failure(self):
    """Test that existing connection parameters are preserved when update fails"""
    # Setup: instance exists in requestinstance-db with connection params
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(new_params, sort_keys=True),
      "{}",
      new_hash,
      "1234567890",
      True
    )])

    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': old_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      '{"param1": "existing_conn1", "param2": "existing_conn2"}',
      old_hash,
      "1234567890",
      True
    )])

    # Make getConnectionParameter fail (simulating instance not ready)
    from slapos import slap as slapmodule
    self.instance_getConnectionParameter.side_effect = slapmodule.NotFoundError("Not ready")

    recipe = requestinstancelist.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify instance was updated (error info should be empty for valid instances)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    # Error info should be empty for valid instances
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {})

  def test_publish_connection_parameters_on_validation_failure(self):
    """Test that connection parameters are published when validation fails"""
    # Create a custom recipe class that returns connection parameters on validation failure
    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Validation failed'], {'message': 'Error message', 'errors': ['Validation failed']}

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was called with validation error parameters
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(conn_params['message'], 'Error message')
    self.assertEqual(conn_params['errors'], ['Validation failed'])

  def test_publish_connection_parameters_on_validation_success(self):
    """Test that success message is published when validation succeeds with validation_conn_params"""
    # Create a custom recipe class that returns connection parameters on validation success
    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return True, [], {'message': 'Success message'}

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was called with success message
    # When validation succeeds and validation_conn_params exist, a success message is published
    # (not the validation_conn_params themselves)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(conn_params['message'], 'Your instance is valid the request has been transmitted to the master')

  def test_publish_connection_parameters_empty(self):
    """Test that empty connection parameters are not published"""
    # Create a custom recipe class that returns empty connection parameters
    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Validation failed'], {}  # Empty conn_params

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was NOT called (empty conn_params)
    self.setConnectionDict.assert_not_called()

  def test_publish_connection_parameters_none(self):
    """Test that None connection parameters are not published"""
    # Create a custom recipe class that returns None connection parameters
    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Validation failed'], None  # None conn_params

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was NOT called (None conn_params)
    self.setConnectionDict.assert_not_called()

  def test_publish_connection_parameters_error_handling(self):
    """Test that errors during publishing are logged but don't raise"""
    # Create a custom recipe class that returns connection parameters
    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Validation failed'], {'message': 'Error message'}

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Make setConnectionDict raise an error
    self.setConnectionDict.side_effect = Exception("Publish failed")

    recipe = TestRecipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      # Should not raise
      recipe.install()

    # Verify error was logged (check it's in the log, not the only entry)
    log.check(
      ('test', 'DEBUG', 'Comparison results: 1 added, 0 removed, 0 modified'),
      ('test', 'WARNING', 'Instance instance1 failed validation: Validation failed'),
      ('test', 'WARNING', 'Failed to publish connection parameters for instance instance1: Publish failed'),
      ('test', 'DEBUG', 'Tracking invalid new instance (not requesting): instance1'),
    )

    # Verify instance was still processed (not raised)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')

  def test_publish_connection_parameters_uses_connection_cache(self):
    """Test that connection cache is used for computer partition"""
    # Create two recipe instances
    self._createInstanceDB([
      ('instance1', {'key': 'value1'}, True),
      ('instance2', {'key': 'value2'}, True)
    ])

    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Validation failed'], {'message': 'Error for %s' % instance_reference}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify registerComputerPartition was only called once (cached)
    self.assertEqual(self.slap_instance_publish.registerComputerPartition.call_count, 1)

    # Verify both calls used setConnectionDict with the same computer_partition
    self.assertEqual(self.setConnectionDict.call_count, 2)
    # Both should have been called with the same computer_partition instance
    self.setConnectionDict.assert_any_call({'message': 'Error for instance1'}, slave_reference='instance1')
    self.setConnectionDict.assert_any_call({'message': 'Error for instance2'}, slave_reference='instance2')

  def test_publish_connection_parameters_missing_slap_connection(self):
    """Test that missing slap-connection section raises KeyError"""
    # Buildout without slap-connection section
    buildout_no_connection = {
      "buildout": {},
    }

    recipe = requestinstancelist.Recipe(buildout_no_connection, 'test', self.options)

    # Should raise KeyError when trying to get computer partition (lazy initialization)
    with self.assertRaises(KeyError) as cm:
      recipe._getComputerPartition()

    self.assertIn('slap-connection section is required', str(cm.exception))

  def test_publish_connection_parameters_success_message(self):
    """Test that success message is published when validation succeeds with validation_conn_params"""
    # Create a custom recipe class that returns connection parameters on validation success
    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        # Return validation_conn_params so success message is published
        return True, [], {'some': 'param'}

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was called with success message
    # When validation succeeds and validation_conn_params exist (even if request_conn_params don't),
    # a success message is published
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(conn_params['message'], 'Your instance is valid the request has been transmitted to the master')

  def test_publish_error_info_for_new_invalid_instance(self):
    """Test that error info is published for new invalid instances"""
    validation_errors = {
      'message': 'Invalid parameters: field "name" is required',
      'errors': ['field "name" is required']
    }
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, False)
    ], connection_params={'instance1': validation_errors})

    recipe = requestinstancelist.Recipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify error info was published for new invalid instance
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(conn_params['message'], validation_errors['message'])
    self.assertEqual(conn_params['errors'], validation_errors['errors'])

  def test_publish_error_info_for_modified_invalid_instance(self):
    """Test that error info is published for modified invalid instances with changed error info"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib
    # New parameters (different from old)
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # New error info (different from old)
    new_errors = {
      'message': 'New error: field "value" is required',
      'errors': ['field "value" is required']
    }
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(new_params, sort_keys=True),
      json.dumps(new_errors, sort_keys=True),
      new_hash,
      "1234567890",
      False
    )])

    # Old parameters and error info in requestinstancedb
    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': old_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    old_errors = {
      'message': 'Old error: field "name" is required',
      'errors': ['field "name" is required']
    }
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      json.dumps(old_errors, sort_keys=True),
      old_hash,
      "1234567890",
      False
    )])

    recipe = requestinstancelist.Recipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify new error info was published (different from stored)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    # Should publish new error info, not old
    self.assertEqual(conn_params['message'], new_errors['message'])
    self.assertEqual(conn_params['errors'], new_errors['errors'])
    self.assertNotEqual(conn_params['message'], old_errors['message'])

  def test_publish_error_info_for_unchanged_invalid_instance(self):
    """Test that error info is published for unchanged invalid instances when error info changes"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib
    # Same parameters (not modified)
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': params}, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # New error info (different from old, even though parameters didn't change)
    new_errors = {
      'message': 'New error: field "value" is required',
      'errors': ['field "value" is required']
    }
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(new_errors, sort_keys=True),
      instance_hash,
      "1234567890",
      False
    )])

    # Old error info in requestinstancedb (same parameters, different error)
    old_errors = {
      'message': 'Old error: field "name" is required',
      'errors': ['field "name" is required']
    }
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(old_errors, sort_keys=True),
      instance_hash,  # Same hash (parameters didn't change)
      "1234567890",
      False
    )])

    recipe = requestinstancelist.Recipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify new error info was published (error info changed even though parameters didn't)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    # Should publish new error info, not old
    self.assertEqual(conn_params['message'], new_errors['message'])
    self.assertEqual(conn_params['errors'], new_errors['errors'])
    self.assertNotEqual(conn_params['message'], old_errors['message'])

  def test_json_error_read_from_database_for_invalid_instances(self):
    """Test that json_error is actually read from database for invalid instances"""
    # This test directly verifies that _getUpdateList reads json_error for invalid instances
    # If the bug is active (checking valid_parameter), this test will fail
    validation_errors = {
      'message': 'Test error from database',
      'errors': ['Error 1', 'Error 2']
    }
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, False)  # invalid instance
    ], connection_params={'instance1': validation_errors})

    recipe = requestinstancelist.Recipe(self.buildout, 'test', self.options)

    # Directly test _getUpdateList to verify json_error is read
    update_list = recipe._getUpdateList()

    # Find our instance
    instance1 = None
    for item in update_list:
      if item['reference'] == 'instance1':
        instance1 = item
        break

    self.assertIsNotNone(instance1, "instance1 should be in update list")
    self.assertFalse(instance1['valid'], "instance1 should be invalid")

    # CRITICAL: Verify that error_info was read from json_error
    # If the bug is active (if row.get('valid_parameter') and row.get('json_error')),
    # error_info would be {} (empty) because valid_parameter is False
    self.assertNotEqual(instance1['error_info'], {},
                       "json_error was not read from database - bug is present! "
                       "error_info should contain validation errors but is empty. "
                       "This means the condition 'if row.get('valid_parameter') and row.get('json_error')' "
                       "is preventing json_error from being read for invalid instances.")
    self.assertEqual(instance1['error_info']['message'], validation_errors['message'])
    self.assertEqual(instance1['error_info']['errors'], validation_errors['errors'])

  def test_publish_validation_errors_from_database(self):
    """Test that validation errors from the database (from JsonSchemaWithDB) are published for new invalid instances"""
    validation_errors = {
      'message': 'Invalid parameters: field "name" is required',
      'errors': ['field "name" is required', 'field "value" must be an integer']
    }
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, False)
    ], connection_params={'instance1': validation_errors})

    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Different error from validateInstance'], {'message': 'Different error'}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    with LogCapture() as log:
      recipe.install()
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    self.assertNotEqual(conn_params, {}, "json_error from database was not read - bug is present!")
    self.assertEqual(conn_params['message'], validation_errors['message'])
    self.assertEqual(conn_params['errors'], validation_errors['errors'])

  def test_publish_validation_errors_from_database_modified(self):
    """Test that validation errors from the database are published for modified invalid instances"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    import hashlib
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': new_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()

    validation_errors = {
      'message': 'Invalid parameters: field "name" is required',
      'errors': ['field "name" is required']
    }
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(new_params, sort_keys=True),
      json.dumps(validation_errors, sort_keys=True),
      new_hash,
      "1234567890",
      False
    )])

    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps({'reference': 'instance1', 'parameters': old_params}, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      "{}",
      old_hash,
      "1234567890",
      True
    )])

    class TestRecipe(requestinstancelist.Recipe):
      def validateInstance(self, instance_reference, parameters):
        return False, ['Different error from validateInstance'], {'message': 'Different error'}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify error info from database was published (not from validateInstance)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    self.assertEqual(conn_params['message'], validation_errors['message'])
    self.assertEqual(conn_params['errors'], validation_errors['errors'])
