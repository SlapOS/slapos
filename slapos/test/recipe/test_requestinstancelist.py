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

  def _createInstanceDB(self, instances):
    """Helper to populate instance database"""
    db = HostedInstanceLocalDB(self.instance_db_path)
    instance_list = []
    for ref, params, valid in instances:
      params_json = json.dumps(params, sort_keys=True)
      # Create a simple hash for testing
      import hashlib
      instance_hash = hashlib.sha256(
        json.dumps({'reference': ref, 'parameters': params}, sort_keys=True).encode('utf-8')
      ).hexdigest()
      instance_list.append((
        ref,
        params_json,
        "{}",  # connection params
        instance_hash,
        "1234567890",
        valid
      ))
    db.insertInstanceList(instance_list)

  def _getRequestInstanceDB(self):
    """Helper to get request instance database contents"""
    db = HostedInstanceLocalDB(self.requestinstance_db_path)
    return db.getInstanceList("reference, json_parameters, json_connection_parameters, valid_parameter")

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
    stored_conn = json.loads(stored[0]['json_connection_parameters'])
    self.assertEqual(stored_conn, {})

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
    # Connection parameters are not extracted since 'return' is not a recipe option
    # But existing connection parameters should be preserved
    stored_conn = json.loads(stored[0]['json_connection_parameters'])
    self.assertEqual(stored_conn, {'param1': 'old_conn1'})  # Preserved from old instance

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
    # Connection parameters are not extracted since 'return' is not a recipe option
    # But existing connection parameters should be preserved
    stored_conn = json.loads(stored[0]['json_connection_parameters'])
    self.assertEqual(stored_conn, {'param1': 'old_conn1'})  # Preserved from old instance

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
    stored_conn = json.loads(stored[0]['json_connection_parameters'])
    self.assertEqual(stored_conn, {})

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

    # Verify instance was updated (connection parameters are not extracted)
    stored = self._getRequestInstanceDB()
    self.assertEqual(len(stored), 1)
    # Connection parameters are not extracted since 'return' is not a recipe option
    # But existing connection parameters should be preserved
    stored_conn = json.loads(stored[0]['json_connection_parameters'])
    self.assertEqual(stored_conn, {'param1': 'existing_conn1', 'param2': 'existing_conn2'})  # Preserved
