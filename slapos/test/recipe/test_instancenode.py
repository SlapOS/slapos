import json
import hashlib
import fcntl
import mock
import os
import sys
import tempfile
import unittest
from collections import defaultdict

from slapos.recipe import instancenode
from slapos.recipe.localinstancedb import HostedInstanceLocalDB
from testfixtures import LogCapture


class TestRequestInstanceList(unittest.TestCase):

  def setUp(self):
    # Create temporary databases
    self.instance_db_fd, self.instance_db_path = tempfile.mkstemp()
    self.requestinstance_db_fd, self.requestinstance_db_path = tempfile.mkstemp()

    # Setup buildout
    # buildout is no longer used, set to None
    self.buildout = None

    # Mock slap library (used by both _requestInstance and _publishConnectionParameters)
    # The code uses 'from slapos import slap', so we need to mock it where it's used
    slap_patch = mock.patch('slapos.recipe.instancenode.slap')
    self.slap_lib = slap_patch.start()
    self.addCleanup(slap_patch.stop)

    # Mock getConnectionParameterDict to return dict by default
    # Use a function that returns a dict to ensure it's always a real dict, not a MagicMock
    def default_get_connection_parameter_dict():
      return {"foo": "bar"}

    # Create a mock that uses side_effect to call the function
    # This ensures it always returns a real dict, not a MagicMock
    get_conn_param_dict_mock = mock.MagicMock(side_effect=default_get_connection_parameter_dict)

    # Create requested_instance with getConnectionParameterDict already set
    # This prevents the mock chain from creating a new MagicMock
    self.requested_instance = mock.MagicMock()
    self.requested_instance.getConnectionParameterDict = get_conn_param_dict_mock

    # Mock getConnectionParameter
    self.instance_getConnectionParameter = \
        self.requested_instance.getConnectionParameter

    # Setup mock computer partition (used by both requesting and publishing)
    # Since _getComputerPartition() uses connection cache, both paths use the same instance
    self.computer_partition = mock.MagicMock()

    # Setup request() method for requesting instances
    self.request_instance = mock.MagicMock()
    self.request_instance.return_value = self.requested_instance
    self.computer_partition.request = self.request_instance

    # Setup setConnectionDict() method for publishing
    self.setConnectionDict = mock.MagicMock()
    self.computer_partition.setConnectionDict = self.setConnectionDict

    # Setup mock slap instance (used by _getComputerPartition)
    self.slap_instance = mock.MagicMock()
    self.slap_instance.registerComputerPartition.return_value = self.computer_partition

    # Setup mock slap class
    self.slap_class = mock.MagicMock()
    self.slap_class.return_value = self.slap_instance
    self.slap_lib.slap = self.slap_class

    # Store reference so tests can modify side_effect
    self.getConnectionParameterDict_mock = get_conn_param_dict_mock

    # Clear connection cache before each test
    from slapos.recipe.librecipe.genericslap import CONNECTION_CACHE
    CONNECTION_CACHE.clear()

    # Reset logging handlers to ensure LogCapture works properly
    # This is needed because configure_logging tests may have set up handlers
    import logging
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    # Also ensure the 'test' logger (used by Recipe) can emit DEBUG messages
    test_logger = logging.getLogger('test')
    test_logger.setLevel(logging.DEBUG)

    # Default options
    # Note: We don't set logfile or debug in test options to allow LogCapture to work
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
      instance_hash = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode('utf-8')
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

    recipe = instancenode.Recipe(
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
    # Connection parameters are stored in json_error for valid instances
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {"foo": "bar"})
    # Instance should be valid since connection parameters were available
    self.assertEqual(stored[0]['valid_parameter'], True)

  def test_new_invalid_instance(self):
    """Test that invalid instances are tracked but not requested"""
    # Setup: one invalid instance in instance-db
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, False)
    ])

    recipe = instancenode.Recipe(
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
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'message': 'Instance validation failed'}"),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )

  def test_modified_valid_instance(self):
    """Test updating a modified valid instance"""
    # Setup: instance exists in both DBs with different parameters
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Add to instance-db with new parameters
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
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

    recipe = instancenode.Recipe(
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
    # Connection parameters are stored in json_error for valid instances
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {"foo": "bar"})
    # Instance should be valid since connection parameters were available
    self.assertEqual(stored[0]['valid_parameter'], True)

  def test_modified_invalid_instance(self):
    """Test that modified invalid instances are tracked but not requested"""
    # Setup: instance exists in both DBs, but now invalid
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      '{"param1": "old_conn1"}',
      old_hash,
      "1234567890",
      True
    )])

    recipe = instancenode.Recipe(
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
    # Error info should contain the default message for invalid instances when no errors are provided
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {'message': 'Instance validation failed'})

    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 1 modified'),
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'message': 'Instance validation failed'}"),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )

  def test_destroyed_instance(self):
    """Test destroying a removed instance"""
    # Setup: instance exists in requestinstance-db but not in instance-db
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      '{"param1": "conn1"}',
      instance_hash,
      "1234567890",
      True
    )])

    recipe = instancenode.Recipe(
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

    # New valid instance
    new_params = {'key': 'new'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(mod_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
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
      json.dumps(destroy_params, sort_keys=True).encode('utf-8')
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

    recipe = instancenode.Recipe(
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

    recipe = instancenode.Recipe(
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
    new_params = {'key': 'value3'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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

    recipe = instancenode.Recipe(
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

    recipe = instancenode.Recipe(
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

    recipe = instancenode.Recipe(
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

    recipe = instancenode.Recipe(
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
      instancenode.Recipe(self.buildout, 'test', options)

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
      instancenode.Recipe(self.buildout, 'test', options)

    self.assertIn('software-type is required', str(cm.exception))

  def test_no_instances(self):
    """Test behavior when there are no instances"""
    # Empty databases
    recipe = instancenode.Recipe(
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

    recipe = instancenode.Recipe(
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

    recipe = instancenode.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify default state 'started' was used
    self.request_instance.assert_called_once()
    call_kwargs = self.request_instance.call_args[1]
    self.assertEqual(call_kwargs['state'], 'started')

  def test_request_name_prefix_new_instance(self):
    """Test that request-name-prefix is applied to new instance requests"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    options = self.options.copy()
    options['request-name-prefix'] = 'prefix-'

    recipe = instancenode.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify request was made with prefixed name
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][2], 'prefix-instance1')  # name parameter with prefix

    # Verify local database still uses original reference (no prefix)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')  # Original reference, no prefix

  def test_request_name_prefix_modified_instance(self):
    """Test that request-name-prefix is applied to modified instance requests"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Add to instance-db with new parameters
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      '{"param1": "old_conn1"}',
      old_hash,
      "1234567890",
      True
    )])

    options = self.options.copy()
    options['request-name-prefix'] = 'prefix-'

    recipe = instancenode.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify request was made with prefixed name
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][2], 'prefix-instance1')  # name parameter with prefix

    # Verify local database still uses original reference (no prefix)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')  # Original reference, no prefix

  def test_request_name_prefix_destroyed_instance(self):
    """Test that request-name-prefix is applied to destroyed instance requests"""
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      '{"param1": "conn1"}',
      instance_hash,
      "1234567890",
      True
    )])

    options = self.options.copy()
    options['request-name-prefix'] = 'prefix-'

    recipe = instancenode.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify destroy was requested with prefixed name
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][2], 'prefix-instance1')  # name parameter with prefix
    call_kwargs = self.request_instance.call_args[1]
    self.assertEqual(call_kwargs['state'], 'destroyed')

  def test_request_name_prefix_multiple_instances(self):
    """Test that request-name-prefix is applied to all instance requests"""
    self._createInstanceDB([
      ('instance1', {'key': 'value1'}, True),
      ('instance2', {'key': 'value2'}, True)
    ])

    options = self.options.copy()
    options['request-name-prefix'] = 'prefix-'

    recipe = instancenode.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify both requests were made with prefixed names
    self.assertEqual(self.request_instance.call_count, 2)
    call_args_list = self.request_instance.call_args_list
    requested_names = [call[0][2] for call in call_args_list]
    self.assertIn('prefix-instance1', requested_names)
    self.assertIn('prefix-instance2', requested_names)

    # Verify local database still uses original references (no prefix)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 2)
    stored_refs = {row['reference'] for row in stored}
    self.assertEqual(stored_refs, {'instance1', 'instance2'})  # Original references, no prefix

  def test_request_name_prefix_default_empty(self):
    """Test that request-name-prefix defaults to empty string (no prefix)"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Don't set request-name-prefix option
    recipe = instancenode.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify request was made without prefix
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][2], 'instance1')  # name parameter without prefix

  def test_request_name_prefix_empty_string(self):
    """Test that empty request-name-prefix works the same as default"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    options = self.options.copy()
    options['request-name-prefix'] = ''

    recipe = instancenode.Recipe(
      self.buildout, 'test', options
    )
    recipe.install()

    # Verify request was made without prefix
    self.request_instance.assert_called_once()
    call_args = self.request_instance.call_args
    self.assertEqual(call_args[0][2], 'instance1')  # name parameter without prefix

  def test_request_failure_handling(self):
    """Test that request failures are handled gracefully"""
    # Request failures are caught by deployInstance, so instance will be tracked as invalid
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Make request fail
    from slapos import slap as slapmodule
    self.request_instance.side_effect = slapmodule.NotFoundError("Not found")

    recipe = instancenode.Recipe(
      None, 'test', self.options
    )

    # Should not raise - deployInstance catches exceptions
    recipe.install()

    # Instance should be tracked in DB as invalid (deployInstance returned False)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], False)

  def test_connection_parameters_preserved_on_update_failure(self):
    """Test that existing connection parameters are preserved when update fails"""
    # Setup: instance exists in requestinstance-db with connection params
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
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
    # Set side_effect to a callable that raises the exception
    # This ensures the exception is raised when the mock is called
    def raise_not_found_error():
      raise slapmodule.NotFoundError("Not ready")
    self.getConnectionParameterDict_mock.side_effect = raise_not_found_error
    # CRITICAL: Also set it directly on requested_instance to ensure it's used
    # The mock chain might create a new MagicMock if we don't set it explicitly
    self.requested_instance.getConnectionParameterDict = self.getConnectionParameterDict_mock

    recipe = instancenode.Recipe(
      self.buildout, 'test', self.options
    )
    recipe.install()

    # Verify instance was updated
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    # When getConnectionParameterDict raises an exception, valid should be False
    # and a message dict is published
    stored_error = json.loads(stored[0]['json_error'])
    self.assertEqual(stored_error, {'message': 'Your instance is valid the request has been transmitted to the master'})
    # Instance should be invalid since connection parameters were not available (exception raised)
    self.assertEqual(stored[0]['valid_parameter'], False)

  def test_publish_connection_parameters_on_validation_failure(self):
    """Test that connection parameters are published when validation fails"""
    # Create a custom recipe class that returns connection parameters on validation failure
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
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
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
        return True, [], {'message': 'Success message'}

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Mock request to return empty connection parameters so success message is published
    self.getConnectionParameterDict_mock.side_effect = lambda: {}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was called with success message
    # When validation succeeds and request_conn_params are empty, a success message is published
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(conn_params['message'], 'Your instance is valid the request has been transmitted to the master, waiting for its connection parameters')

    # Verify instance is invalid since getConnectionParameterDict returned empty dict
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], False)

  def test_publish_connection_parameters_empty(self):
    """Test that empty connection parameters are not published"""
    # Create a custom recipe class that returns empty connection parameters
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
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
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
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
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
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
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'message': 'Error message'}"),
      ('test', 'WARNING', 'Failed to publish connection parameters for instance instance1: Publish failed'),
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

    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
        return False, ['Validation failed'], {'message': 'Error for %s' % instance_reference}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify registerComputerPartition was only called once (cached)
    self.assertEqual(self.slap_instance.registerComputerPartition.call_count, 1)

    # Verify both calls used setConnectionDict with the same computer_partition
    self.assertEqual(self.setConnectionDict.call_count, 2)
    # Both should have been called with the same computer_partition instance
    self.setConnectionDict.assert_any_call({'message': 'Error for instance1'}, slave_reference='instance1')
    self.setConnectionDict.assert_any_call({'message': 'Error for instance2'}, slave_reference='instance2')

  def test_publish_connection_parameters_missing_slap_connection(self):
    """Test that missing connection parameters raise error"""
    # Options without required connection parameters
    options_no_connection = self.options.copy()
    del options_no_connection['server-url']

    # Should raise KeyError during initialization when accessing options['server-url']
    with self.assertRaises(KeyError):
      instancenode.Recipe(None, 'test', options_no_connection)

  def test_publish_connection_parameters_success_message(self):
    """Test that success message is published when validation succeeds with validation_conn_params"""
    # Create a custom recipe class that returns connection parameters on validation success
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
        # Return validation_conn_params so success message is published
        return True, [], {'some': 'param'}

    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Mock request to return empty connection parameters so success message is published
    self.getConnectionParameterDict_mock.side_effect = lambda: {}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was called with success message
    # When validation succeeds and request_conn_params are empty, a success message is published
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(conn_params['message'], 'Your instance is valid the request has been transmitted to the master, waiting for its connection parameters')

    # Verify instance is invalid since getConnectionParameterDict returned empty dict
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], False)

  def test_publish_error_info_for_new_invalid_instance(self):
    """Test that error info is published for new invalid instances"""
    validation_errors = {
      'message': 'Invalid parameters: field "name" is required',
      'errors': ['field "name" is required']
    }
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, False)
    ], connection_params={'instance1': validation_errors})

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)
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

    # New parameters (different from old)
    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
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

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)
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

  def test_removed_invalid_instance_re_validation(self):
    """Test that removed invalid instances are not re-processed for re-validation

    Previously invalid instances that haven't changed (not in 'modified' or 'removed')
    should not be re-processed for re-validation.
    """
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Same parameters in both DBs (unchanged)
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # Same error info in both DBs (unchanged)
    error_info = {
      'message': 'Validation error: field "name" is required',
      'errors': ['field "name" is required']
    }

    # Add to requestinstance-db (same parameters, same hash, invalid)
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(error_info, sort_keys=True),
      instance_hash,  # Same hash (parameters didn't change)
      "1234567890",
      False  # invalid
    )])


    recipe = instancenode.Recipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify instance was removed from requestinstance-db
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 0)

  def test_unchanged_invalid_instance_re_validation(self):
    """Test that unchanged invalid instances are re-processed for re-validation

    Invalid instances that haven't changed (not in 'modified' or 'removed')
    should still be processed for re-validation. This ensures that if validation logic
    changes or external conditions change, invalid instances get re-checked.

    Key conditions:
    - Instance exists in both instance-db and requestinstance-db
    - Same parameters (same hash) - NOT in 'modified'
    - Instance exists in instance-db - NOT in 'removed'
    - Instance is invalid in requestinstance-db
    - Should be processed (preDeployInstanceValidation called)
    """
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)


    # Same error info in both DBs (unchanged)
    error_info = {
      'message': 'Validation error: field "name" is required',
      'errors': ['field "name" is required']
    }

    # Same parameters in both DBs (unchanged - same hash)
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    # Add to instance-db (invalid, unchanged - same hash as requestinstance-db)
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(error_info, sort_keys=True),
      instance_hash,
      "1234567890",
      True  # invalid
    )])

    # Add to requestinstance-db (same parameters, same hash, invalid)
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(error_info, sort_keys=True),
      instance_hash,  # Same hash (parameters didn't change) - NOT in 'modified'
      "1234567890",
      False  # invalid
    )])

    # Create a custom recipe to track if preDeployInstanceValidation was called
    validation_calls = []
    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
        validation_calls.append((instance_reference, parameters))
        # Return same validation result (still invalid)
        return False, ['Validation error: field "name" is required'], error_info

    recipe = TestRecipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # CRITICAL: Verify that preDeployInstanceValidation was called for the unchanged invalid instance
    # This ensures the bug fix is working - unchanged invalid instances should be re-validated
    # The instance is NOT in 'modified' (same hash) and NOT in 'removed' (exists in instance-db)
    # So it should be in unchanged_invalid_instances_to_process and processed
    self.assertEqual(len(validation_calls), 1,
                    "preDeployInstanceValidation should be called once for unchanged invalid instance. "
                    "The instance is not in 'modified' (same hash) and not in 'removed' (exists in instance-db), "
                    "so it should be added to unchanged_invalid_instances_to_process and processed.")
    self.assertEqual(validation_calls[0][0], 'instance1')
    self.assertEqual(validation_calls[0][1], params)

    # Verify error info was not published (re-validation happened)
    # But same error as before, so no republishing
    self.setConnectionDict.assert_not_called()

    # Verify instance was NOT requested (still invalid)
    self.request_instance.assert_not_called()

    # Verify instance is still tracked in requestinstance-db
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['reference'], 'instance1')
    self.assertEqual(stored[0]['valid_parameter'], False)

    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 0 modified'),
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'message': 'Validation error: field \"name\" is required', 'errors': ['field \"name\" is required']}"),
      ('test', 'DEBUG', 'Connection parameters for instance instance1 unchanged, skipping publish'),
    )

  def test_publish_error_info_for_unchanged_invalid_instance(self):
    """Test that error info is published for unchanged invalid instances when error info changes"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Same parameters (not modified)
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
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

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)
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

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

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

    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
        return False, ['Different error from preDeployInstanceValidation'], {'message': 'Different error'}

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

    new_params = {'key': 'new_value'}
    new_hash = hashlib.sha256(
      json.dumps(new_params, sort_keys=True).encode('utf-8')
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
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      "{}",
      old_hash,
      "1234567890",
      True
    )])

    class TestRecipe(instancenode.Recipe):
      def preDeployInstanceValidation(self, instance_reference, parameters):
        return False, ['Different error from preDeployInstanceValidation'], {'message': 'Different error'}

    recipe = TestRecipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify error info from database was published (not from preDeployInstanceValidation)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    conn_params = call_args[0][0]
    self.assertEqual(conn_params['message'], validation_errors['message'])
    self.assertEqual(conn_params['errors'], validation_errors['errors'])

  def test_publish_connection_parameters_unchanged_skips_publish(self):
    """Test that unchanged connection parameters are not republished"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Use slightly different parameters so instance is in "modified" and gets processed
    # but connection parameters are the same
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # Same connection parameters in both DBs (unchanged)
    # When getConnectionParameterDict returns empty dict, this message is generated
    conn_params = {
      'message': 'Your instance is valid the request has been transmitted to the master, waiting for its connection parameters'
    }

    # Add to instance-db
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(conn_params, sort_keys=True),
      instance_hash,
      "1234567890",
      True
    )])

    # Add to requestinstance-db with same connection parameters but different hash
    # (to make it appear in "modified")
    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      json.dumps(conn_params, sort_keys=True),
      old_hash,  # Different hash (parameters changed, so in "modified")
      "1234567890",
      True
    )])

    # Mock request to return same connection parameters (empty dict -> success message)
    self.getConnectionParameterDict_mock.side_effect = lambda: {}

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was NOT called (connection parameters unchanged)
    # Even though instance was processed, connection params are the same
    self.setConnectionDict.assert_not_called()

    # Verify instance is invalid since getConnectionParameterDict returned empty dict
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], False)

    # Verify log shows instance was processed and skipping publish
    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 1 modified'),
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'message': 'Your instance is valid the request has been transmitted to the master, waiting for its connection parameters'}"),
      ('test', 'DEBUG', 'Connection parameters for instance instance1 unchanged, skipping publish'),
    )

  def test_publish_connection_parameters_changed_republishes(self):
    """Test that changed connection parameters are republished"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Use slightly different parameters so instance is in "modified" and gets processed
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # New connection parameters (different from stored)
    new_conn_params = {
      'message': 'Your instance is valid the request has been transmitted to the master',
      'url': 'https://new.example.com'
    }

    # Old connection parameters (different from new)
    old_conn_params = {
      'message': 'Your instance is valid the request has been transmitted to the master'
    }

    # Add to instance-db with new connection parameters
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(new_conn_params, sort_keys=True),
      instance_hash,
      "1234567890",
      True
    )])

    # Add to requestinstance-db with old connection parameters but different hash
    # (to make it appear in "modified")
    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      json.dumps(old_conn_params, sort_keys=True),
      old_hash,  # Different hash (parameters changed, so in "modified")
      "1234567890",
      True
    )])

    # Mock request to return new connection parameters
    self.getConnectionParameterDict_mock.side_effect = lambda: new_conn_params

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was called (connection parameters changed)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    published_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(published_params, new_conn_params)
    self.assertIn('url', published_params)

    # Verify instance is valid since connection parameters were available
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], True)

    # Verify log shows publishing
    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 1 modified'),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )

  def test_publish_connection_parameters_new_instance_always_publishes(self):
    """Test that new instances always publish (no previous data to compare)"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Mock request to return connection parameters
    conn_params = {
      'url': 'https://example.com',
      'port': '8080'
    }
    self.getConnectionParameterDict_mock.side_effect = lambda: conn_params

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was called (new instance, no previous data)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    published_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(published_params, conn_params)

    # Verify instance is valid since connection parameters were available
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], True)

    # Verify log shows publishing
    log.check(
      ('test', 'DEBUG', 'Comparison results: 1 added, 0 removed, 0 modified'),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )

  def test_publish_connection_parameters_invalid_unchanged_skips_publish(self):
    """Test that unchanged validation errors for invalid instances are not republished"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Same parameters (not modified)
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # Same validation errors in both DBs (unchanged)
    validation_errors = {
      'message': 'Validation error: field "name" is required',
      'errors': ['field "name" is required']
    }

    # Add to instance-db
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(validation_errors, sort_keys=True),
      instance_hash,
      "1234567890",
      False
    )])

    # Add to requestinstance-db with same validation errors
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(validation_errors, sort_keys=True),
      instance_hash,  # Same hash (parameters didn't change)
      "1234567890",
      False
    )])

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was NOT called (validation errors unchanged)
    self.setConnectionDict.assert_not_called()

    # Verify log shows skipping publish (instance is processed as unchanged invalid)
    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 0 modified'),
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'errors': ['field \"name\" is required'], 'message': 'Validation error: field \"name\" is required'}"),
      ('test', 'DEBUG', 'Connection parameters for instance instance1 unchanged, skipping publish'),
    )

  def test_publish_connection_parameters_invalid_changed_republishes(self):
    """Test that changed validation errors for invalid instances are republished"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    # Same parameters (not modified)
    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    # New validation errors (different from stored)
    new_errors = {
      'message': 'New validation error: field "value" is required',
      'errors': ['field "value" is required']
    }

    # Old validation errors (different from new)
    old_errors = {
      'message': 'Old validation error: field "name" is required',
      'errors': ['field "name" is required']
    }

    # Add to instance-db with new validation errors
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(new_errors, sort_keys=True),
      instance_hash,
      "1234567890",
      False
    )])

    # Add to requestinstance-db with old validation errors
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(old_errors, sort_keys=True),
      instance_hash,  # Same hash (parameters didn't change)
      "1234567890",
      False
    )])

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was called (validation errors changed)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    published_params = call_args[0][0]
    slave_ref = call_args[1]['slave_reference']

    self.assertEqual(slave_ref, 'instance1')
    self.assertEqual(published_params['message'], new_errors['message'])
    self.assertEqual(published_params['errors'], new_errors['errors'])

    # Verify log shows publishing
    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 0 modified'),
      ('test', 'DEBUG', "Instance instance1 failed validation and needs reprocessing: {'errors': ['field \"value\" is required'], 'message': 'New validation error: field \"value\" is required'}"),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )

  def test_publish_connection_parameters_no_stored_instance_publishes(self):
    """Test that publishing works when no stored instance exists (new instance)"""
    self._createInstanceDB([
      ('instance1', {'key': 'value'}, True)
    ])

    # Mock request to return connection parameters
    conn_params = {'url': 'https://example.com'}
    self.getConnectionParameterDict_mock.side_effect = lambda: conn_params

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)
    recipe.install()

    # Verify setConnectionDict was called (no stored instance to compare)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    published_params = call_args[0][0]
    self.assertEqual(published_params, conn_params)

    # Verify instance is valid since connection parameters were available
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], True)

  def test_publish_connection_parameters_invalid_json_error_republishes(self):
    """Test that invalid json_error in database causes republish (can't compare)"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    conn_params = {
      'message': 'Your instance is valid the request has been transmitted to the master'
    }

    # Add to instance-db
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(conn_params, sort_keys=True),
      instance_hash,
      "1234567890",
      True
    )])

    # Add to requestinstance-db with invalid JSON in json_error and different hash
    # (to make it appear in "modified")
    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      'invalid json{',  # Invalid JSON
      old_hash,  # Different hash (parameters changed, so in "modified")
      "1234567890",
      True
    )])

    # Mock request to return connection parameters
    self.getConnectionParameterDict_mock.side_effect = lambda: conn_params

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was called (invalid JSON, can't compare, so publish)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    published_params = call_args[0][0]
    self.assertEqual(published_params, conn_params)

    # Verify instance is valid since connection parameters were available
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], True)

    # Verify log shows publishing
    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 1 modified'),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )

  def test_publish_connection_parameters_empty_json_error_publishes(self):
    """Test that empty json_error in database causes publish (nothing to compare)"""
    instance_db = HostedInstanceLocalDB(self.instance_db_path)
    requestinstance_db = HostedInstanceLocalDB(self.requestinstance_db_path)

    params = {'key': 'value'}
    instance_hash = hashlib.sha256(
      json.dumps(params, sort_keys=True).encode('utf-8')
    ).hexdigest()

    conn_params = {
      'message': 'Your instance is valid the request has been transmitted to the master'
    }

    # Add to instance-db
    instance_db.insertInstanceList([(
      'instance1',
      json.dumps(params, sort_keys=True),
      json.dumps(conn_params, sort_keys=True),
      instance_hash,
      "1234567890",
      True
    )])

    # Add to requestinstance-db with empty json_error and different hash
    # (to make it appear in "modified")
    old_params = {'key': 'old_value'}
    old_hash = hashlib.sha256(
      json.dumps(old_params, sort_keys=True).encode('utf-8')
    ).hexdigest()
    requestinstance_db.insertInstanceList([(
      'instance1',
      json.dumps(old_params, sort_keys=True),
      "{}",  # Empty JSON
      old_hash,  # Different hash (parameters changed, so in "modified")
      "1234567890",
      True
    )])

    # Mock request to return connection parameters
    self.getConnectionParameterDict_mock.side_effect = lambda: conn_params

    recipe = instancenode.Recipe(self.buildout, 'test', self.options)

    with LogCapture() as log:
      recipe.install()

    # Verify setConnectionDict was called (empty JSON, nothing to compare, so publish)
    self.setConnectionDict.assert_called_once()
    call_args = self.setConnectionDict.call_args
    published_params = call_args[0][0]
    self.assertEqual(published_params, conn_params)

    # Verify instance is valid since connection parameters were available
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    self.assertEqual(stored[0]['valid_parameter'], True)

    # Verify log shows publishing
    log.check(
      ('test', 'DEBUG', 'Comparison results: 0 added, 0 removed, 1 modified'),
      ('test', 'DEBUG', 'Published connection parameters for instance instance1'),
    )


class TestCommandLineInterface(unittest.TestCase):
  """Tests for command-line interface functions"""

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    self.config_file = os.path.join(self.temp_dir, 'test.cfg')
    self.pidfile = os.path.join(self.temp_dir, 'test.pid')
    # Reset logging to ensure clean state for each test
    import logging
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

  def tearDown(self):
    import shutil
    import logging
    # Reset logging handlers to avoid interfering with other tests
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)
    if os.path.exists(self.temp_dir):
      shutil.rmtree(self.temp_dir)

  def test_parse_config_file(self):
    """Test parse_config_file function"""
    # Create a test config file
    with open(self.config_file, 'w') as f:
      f.write('[slaposinstancenode]\n')
      f.write('instance-db-path = /path/to/instance.db\n')
      f.write('server-url = https://test.example.com\n')

    parser = instancenode.parse_config_file(self.config_file)
    self.assertTrue(parser.has_section('slaposinstancenode'))
    self.assertEqual(parser.get('slaposinstancenode', 'instance-db-path'), '/path/to/instance.db')
    self.assertEqual(parser.get('slaposinstancenode', 'server-url'), 'https://test.example.com')

  def test_parse_config_file_not_exists(self):
    """Test parse_config_file raises SystemExit when file doesn't exist"""
    with self.assertRaises(SystemExit):
      instancenode.parse_config_file('/nonexistent/file.cfg')

  def test_get_config_section(self):
    """Test get_config_section function"""
    from six.moves.configparser import RawConfigParser
    parser = RawConfigParser()
    parser.add_section('test-section')
    parser.set('test-section', 'key1', 'value1')
    parser.set('test-section', 'key2', 'value2')

    section = instancenode.get_config_section(parser, 'test-section')
    self.assertEqual(section['key1'], 'value1')
    self.assertEqual(section['key2'], 'value2')

  def test_get_config_section_not_exists(self):
    """Test get_config_section returns empty dict when section doesn't exist"""
    from six.moves.configparser import RawConfigParser
    parser = RawConfigParser()

    section = instancenode.get_config_section(parser, 'nonexistent')
    self.assertEqual(section, {})

  def test_create_options_dict_from_config(self):
    """Test create_options_dict_from_config function"""
    # Create a test config file
    with open(self.config_file, 'w') as f:
      f.write('[slaposinstancenode]\n')
      f.write('instance-db-path = /path/to/instance.db\n')
      f.write('server-url = https://test.example.com\n')

    parser = instancenode.parse_config_file(self.config_file)
    options = instancenode.create_options_dict_from_config(parser)

    self.assertEqual(options['instance-db-path'], '/path/to/instance.db')
    self.assertEqual(options['server-url'], 'https://test.example.com')

  def test_create_options_dict_from_config_missing_section(self):
    """Test create_options_dict_from_config raises SystemExit when section is missing"""
    from six.moves.configparser import RawConfigParser
    parser = RawConfigParser()

    with self.assertRaises(SystemExit):
      instancenode.create_options_dict_from_config(parser)

  def test_parse_command_line_args(self):
    """Test parse_command_line_args function"""
    import sys
    old_argv = sys.argv
    try:
      sys.argv = ['test', '--cfg', '/path/to/config.cfg', '--pidfile', '/path/to/pidfile.pid']
      args = instancenode.parse_command_line_args()
      self.assertEqual(args.cfg, '/path/to/config.cfg')
      self.assertEqual(args.pidfile, '/path/to/pidfile.pid')
      self.assertIsNone(args.logfile)
      self.assertFalse(args.debug)
    finally:
      sys.argv = old_argv

  def test_parse_command_line_args_no_pidfile(self):
    """Test parse_command_line_args with no pidfile"""
    import sys
    old_argv = sys.argv
    try:
      sys.argv = ['test', '--cfg', '/path/to/config.cfg']
      args = instancenode.parse_command_line_args()
      self.assertEqual(args.cfg, '/path/to/config.cfg')
      self.assertIsNone(args.pidfile)
      self.assertIsNone(args.logfile)
      self.assertFalse(args.debug)
    finally:
      sys.argv = old_argv

  def test_parse_command_line_args_with_logfile(self):
    """Test parse_command_line_args with --logfile"""
    import sys
    old_argv = sys.argv
    try:
      sys.argv = ['test', '--cfg', '/path/to/config.cfg', '--logfile', '/path/to/logfile.log']
      args = instancenode.parse_command_line_args()
      self.assertEqual(args.cfg, '/path/to/config.cfg')
      self.assertEqual(args.logfile, '/path/to/logfile.log')
      self.assertFalse(args.debug)
    finally:
      sys.argv = old_argv

  def test_parse_command_line_args_with_debug(self):
    """Test parse_command_line_args with --debug"""
    import sys
    old_argv = sys.argv
    try:
      sys.argv = ['test', '--cfg', '/path/to/config.cfg', '--debug']
      args = instancenode.parse_command_line_args()
      self.assertEqual(args.cfg, '/path/to/config.cfg')
      self.assertTrue(args.debug)
      self.assertIsNone(args.logfile)
    finally:
      sys.argv = old_argv

  def test_parse_command_line_args_with_all_options(self):
    """Test parse_command_line_args with all options"""
    import sys
    old_argv = sys.argv
    try:
      sys.argv = ['test', '--cfg', '/path/to/config.cfg', '--pidfile', '/path/to/pidfile.pid', '--logfile', '/path/to/logfile.log', '--debug']
      args = instancenode.parse_command_line_args()
      self.assertEqual(args.cfg, '/path/to/config.cfg')
      self.assertEqual(args.pidfile, '/path/to/pidfile.pid')
      self.assertEqual(args.logfile, '/path/to/logfile.log')
      self.assertTrue(args.debug)
    finally:
      sys.argv = old_argv

  def test_parse_command_line_args_missing_cfg(self):
    """Test parse_command_line_args raises SystemExit when --cfg is missing"""
    import sys
    old_argv = sys.argv
    try:
      sys.argv = ['test']
      with self.assertRaises(SystemExit):
        instancenode.parse_command_line_args()
    finally:
      sys.argv = old_argv

  def test_pidfile_lock_acquire_release(self):
    """Test PIDFileLock context manager acquires and releases lock"""
    lock = instancenode.PIDFileLock(self.pidfile)

    # Should be able to acquire lock
    with lock:
      # Lock should be held
      self.assertTrue(os.path.exists(self.pidfile))
      # PID should be written
      with open(self.pidfile, 'r') as f:
        pid = f.read().strip()
        self.assertEqual(pid, str(os.getpid()))

    # Lock should be released after context exit
    # PID file should be removed on successful exit
    self.assertFalse(os.path.exists(self.pidfile))

  def test_pidfile_lock_no_pidfile(self):
    """Test PIDFileLock with None pidfile path"""
    lock = instancenode.PIDFileLock(None)

    # Should work without creating a file
    with lock:
      pass

    # No file should be created
    self.assertFalse(os.path.exists(self.pidfile))

  def test_pidfile_lock_stale_pidfile(self):
    """Test PIDFileLock handles stale PID file (process doesn't exist)"""
    # Create a PID file with a non-existent PID
    with open(self.pidfile, 'w') as f:
      f.write('99999\n')

    lock = instancenode.PIDFileLock(self.pidfile)

    # Should be able to acquire lock (stale PID file removed)
    with lock:
      # Lock should be held
      self.assertTrue(os.path.exists(self.pidfile))
      # PID should be updated
      with open(self.pidfile, 'r') as f:
        pid = f.read().strip()
        self.assertEqual(pid, str(os.getpid()))

  def test_pidfile_lock_existing_process(self):
    """Test PIDFileLock raises SystemExit when another process is running"""
    # Create a PID file with current PID (simulating another instance)
    # and lock it to prevent acquisition
    pidfile_fd = open(self.pidfile, 'w')
    pidfile_fd.write(str(os.getpid()) + '\n')
    pidfile_fd.flush()
    # Lock the file so lock acquisition fails
    fcntl.flock(pidfile_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    # Try to acquire lock - should fail because file is locked
    lock = instancenode.PIDFileLock(self.pidfile)

    # Mock os.kill to return success (process exists)
    with mock.patch('os.kill') as mock_kill:
      mock_kill.return_value = None  # Process exists
      with self.assertRaises(SystemExit) as cm:
        with lock:
          pass
      self.assertIn('Another instance is already running', str(cm.exception))

    # Clean up
    pidfile_fd.close()

  def test_load_config_and_create_objects(self):
    """Test load_config_and_create_objects function"""
    # Create a test config file
    with open(self.config_file, 'w') as f:
      f.write('[slaposinstancenode]\n')
      f.write('instance-db-path = /path/to/instance.db\n')
      f.write('requestinstance-db-path = /path/to/requestinstance.db\n')
      f.write('server-url = https://test.example.com\n')
      f.write('computer-id = test-computer\n')
      f.write('partition-id = test-partition\n')
      f.write('software-url = https://software.example.com\n')
      f.write('software-type = cdn\n')

    options, pidfile_lock = instancenode.load_config_and_create_objects(
      self.config_file, self.pidfile
    )

    self.assertIsNotNone(options)
    self.assertIsNotNone(pidfile_lock)
    self.assertEqual(options['instance-db-path'], '/path/to/instance.db')
    self.assertEqual(options['server-url'], 'https://test.example.com')

  def test_load_config_and_create_objects_with_logfile_and_debug(self):
    """Test load_config_and_create_objects with logfile and debug options"""
    # Create a test config file with logfile and debug
    with open(self.config_file, 'w') as f:
      f.write('[slaposinstancenode]\n')
      f.write('instance-db-path = /path/to/instance.db\n')
      f.write('logfile = /path/to/logfile.log\n')
      f.write('debug = true\n')

    options, pidfile_lock = instancenode.load_config_and_create_objects(
      self.config_file, None
    )

    self.assertIsNotNone(options)
    self.assertEqual(options['logfile'], '/path/to/logfile.log')
    self.assertEqual(options['debug'], 'true')

  def test_load_config_and_create_objects_no_pidfile(self):
    """Test load_config_and_create_objects without pidfile"""
    # Create a test config file
    with open(self.config_file, 'w') as f:
      f.write('[slaposinstancenode]\n')
      f.write('instance-db-path = /path/to/instance.db\n')

    options, pidfile_lock = instancenode.load_config_and_create_objects(
      self.config_file, None
    )

    self.assertIsNotNone(options)
    self.assertIsNone(pidfile_lock)

  def test_configure_logging_to_file(self):
    """Test configure_logging with logfile"""
    import logging
    logfile_path = os.path.join(self.temp_dir, 'test.log')

    # Reset logging configuration
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    instancenode.configure_logging(logfile=logfile_path, debug=False)

    # Verify log file was created
    self.assertTrue(os.path.exists(logfile_path))

    # Verify logging level is INFO
    self.assertEqual(logging.getLogger().level, logging.INFO)

    # Test that logs are written to file
    test_logger = logging.getLogger('test')
    test_logger.setLevel(logging.INFO)
    test_logger.info('Test message')

    # Force flush
    for handler in logging.getLogger().handlers:
      handler.flush()

    # Verify message is in file
    with open(logfile_path, 'r') as f:
      content = f.read()
      self.assertIn('Test message', content)

  def test_configure_logging_to_file_debug(self):
    """Test configure_logging with logfile and debug=True"""
    import logging
    logfile_path = os.path.join(self.temp_dir, 'test_debug.log')

    # Reset logging configuration
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    instancenode.configure_logging(logfile=logfile_path, debug=True)

    # Verify log file was created
    self.assertTrue(os.path.exists(logfile_path))

    # Verify logging level is DEBUG
    self.assertEqual(logging.getLogger().level, logging.DEBUG)

  def test_configure_logging_to_stderr(self):
    """Test configure_logging without logfile (goes to stderr)"""
    import logging
    import sys
    from io import StringIO

    # Reset logging configuration
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    # Capture stderr
    stderr_capture = StringIO()
    old_stderr = sys.stderr
    sys.stderr = stderr_capture

    try:
      instancenode.configure_logging(logfile=None, debug=False)

      # Verify logging level is INFO
      self.assertEqual(logging.getLogger().level, logging.INFO)

      # Verify handler is StreamHandler pointing to stderr
      handlers = logging.getLogger().handlers
      stream_handlers = [h for h in handlers if isinstance(h, logging.StreamHandler)]
      self.assertTrue(len(stream_handlers) > 0)
    finally:
      sys.stderr = old_stderr

  def test_configure_logging_creates_directory(self):
    """Test configure_logging creates logfile directory if it doesn't exist"""
    import logging
    logfile_path = os.path.join(self.temp_dir, 'subdir', 'test.log')

    # Reset logging configuration
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
      root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    # Directory shouldn't exist yet
    logfile_dir = os.path.dirname(logfile_path)
    self.assertFalse(os.path.exists(logfile_dir))

    instancenode.configure_logging(logfile=logfile_path, debug=False)

    # Directory should be created
    self.assertTrue(os.path.exists(logfile_dir))
    self.assertTrue(os.path.exists(logfile_path))
