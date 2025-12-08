import json
import hashlib
import unittest
import sqlite3
import tempfile
import time
import os

from slapos.recipe.localinstancedb import LocalDBAccessor, HostedInstanceLocalDB, InstanceListComparator, SharedInstanceResultDB

class TestLocalDBAccessor(unittest.TestCase):

  def setUp(self):
    self.db_fd, self.db_path = tempfile.mkstemp()
    self.schema = """
      CREATE TABLE IF NOT EXISTS test (
        id INTEGER PRIMARY KEY,
        name TEXT
      );
    """
    self.accessor = LocalDBAccessor(self.db_path, self.schema)

  def tearDown(self):
    os.close(self.db_fd)
    os.unlink(self.db_path)

  def test_create_table(self):
    con = sqlite3.connect(self.db_path)
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test';")
    self.assertEqual(cur.fetchone()[0], 'test')
    con.close()

  def test_execute_and_fetch(self):
    self.accessor.execute('INSERT INTO test (name) VALUES (?)', ('foo',))
    row = self.accessor.fetchOne('SELECT name FROM test WHERE name=?', ('foo',))
    self.assertIsNotNone(row)
    self.assertEqual(row['name'], 'foo')

  def test_fetch_all(self):
    rows = [('bar',), ('baz',)]
    for r in rows:
      self.accessor.execute('INSERT INTO test (name) VALUES (?)', r)
    result = self.accessor.fetchAll('SELECT name FROM test')
    self.assertEqual(sorted([row['name'] for row in result]), ['bar', 'baz'])

  def test_error_on_bad_query(self):
    with self.assertRaises(ValueError):
      self.accessor.execute('INSERT INTO nonexistent_table (name) VALUES (?)', ('foo',))

  def test_insertMany(self):
    rows = [('multi1',), ('multi2',)]
    query = "INSERT INTO test (name) VALUES (?)"
    self.accessor.insertMany(query, rows)
    result = self.accessor.fetchAll('SELECT name FROM test')
    self.assertEqual(sorted([row['name'] for row in result]), ['multi1', 'multi2'])

  def test_removeMany(self):
    rows = [(1, 'multi1'), (2, 'multi2'), (3, 'multi3')]
    query = "INSERT INTO test (id, name) VALUES (?, ?)"
    self.accessor.insertMany(query, rows)
    keys_to_remove = [1, 3]
    delete_query = "DELETE FROM test WHERE id IN ({})"
    self.accessor.removeMany(delete_query, keys_to_remove)
    remaining = self.accessor.fetchAll("SELECT id FROM test")
    self.assertEqual([row['id'] for row in remaining], [2])

  def test_updateMany(self):
    # Insert initial data
    rows = [(1, 'multi1'), (2, 'multi2'), (3, 'multi3')]
    query = "INSERT INTO test (id, name) VALUES (?, ?)"
    self.accessor.insertMany(query, rows)
    # Update data
    update_query = "UPDATE test SET name = ? WHERE id = ?"
    updates = [("multiA", 1),
           ("multiC", 3),]
    self.accessor.updateMany(update_query, updates)
    updated = self.accessor.fetchAll('SELECT id, name FROM test ORDER BY id')
    self.assertEqual(updated[0]['id'], 1)
    self.assertEqual(updated[0]['name'], 'multiA')
    self.assertEqual(updated[1]['id'], 2)
    self.assertEqual(updated[1]['name'], 'multi2')
    self.assertEqual(updated[2]['id'], 3)
    self.assertEqual(updated[2]['name'], 'multiC')


class TestHostedInstanceLocalDB(unittest.TestCase):

  def setUp(self):
    self.db_fd, self.db_path = tempfile.mkstemp()
    self.db = HostedInstanceLocalDB(self.db_path)

  def tearDown(self):
    os.close(self.db_fd)
    os.unlink(self.db_path)

  def test_schema_created(self):
    con = sqlite3.connect(self.db_path)
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instance';")
    self.assertEqual(cur.fetchone()[0], 'instance')
    con.close()

  def test_getInstanceList(self):
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False)
    ]
    self.db.insertInstanceList(instance_rows)
    result = self.db.getInstanceList()
    references = {r["reference"] for r in result}
    self.assertEqual(references, {"ref1", "ref2"})

  def test_getInstanceList_multiple_select(self):
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False)
    ]
    self.db.insertInstanceList(instance_rows)
    result = self.db.getInstanceList("reference, hash, timestamp")
    test_list = [
      ("reference", 0),
      ("hash", 3),
      ("timestamp", 4),
    ]
    for key, index in test_list:
      values = {r[key] for r in result}
      self.assertEqual(values, {r[index] for r in instance_rows})

  def test_getInstance(self):
    row = ("unique_ref", "params", "conn_params", "some_hash", "1762531560", True)
    self.db.insertInstanceList([row])
    out = self.db.getInstance("unique_ref")
    self.assertIsNotNone(out)
    self.assertEqual(out["reference"], row[0])
    self.assertEqual(out["json_parameters"], row[1])
    self.assertEqual(out["json_error"], row[2])
    self.assertEqual(out["hash"], row[3])
    self.assertEqual(out["timestamp"], row[4])
    self.assertEqual(out["valid_parameter"], row[5])

  def test_removeInstanceList(self):
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False),
      ("ref3", "{}", "{}", "hash2", "1762531560", False)
    ]
    self.db.insertInstanceList(instance_rows)
    self.db.removeInstanceList(["ref1", "ref3"])
    result = self.db.getInstanceList()
    references = [r["reference"] for r in result]
    self.assertEqual(references, ["ref2"])

  def test_updateInstanceList(self):
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False),
      ("ref3", "{}", "{}", "hash3", "1762531560", False)
    ]
    self.db.insertInstanceList(instance_rows)
    instance_rows = [
      ("ref1", '{ "updated": 1 }', "{}", "hash1", "1762531541", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False),
      ("ref3", '{ "updated": 1 }', "{}", "hash3", "1762531561", False)
    ]
    update_query = "UPDATE instance SET json_parameters = ?, timestamp = ? WHERE reference = ?"
    update_list = [(instance_rows[0][1], instance_rows[0][4], "ref1"),
             (instance_rows[2][1], instance_rows[2][4], "ref3")]
    self.db.updateInstanceList(update_query, update_list)
    result = self.db.getInstanceList("reference, json_parameters, timestamp")
    test_list = [
      ("reference", 0),
      ("json_parameters", 1),
      ("timestamp", 4),
    ]
    for key, index in test_list:
      values = {r[key] for r in result}
      self.assertEqual(values, {r[index] for r in instance_rows})

  def test_getInstanceList_valid_only(self):
    """Test getInstanceList with valid_only parameter."""
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False),
      ("ref3", "{}", "{}", "hash3", "1762531570", True)
    ]
    self.db.insertInstanceList(instance_rows)
    result = self.db.getInstanceList(valid_only=True)
    references = {r["reference"] for r in result}
    self.assertEqual(references, {"ref1", "ref3"})

  def test_getInstanceList_invalid_only(self):
    """Test getInstanceList with invalid_only parameter."""
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False),
      ("ref3", "{}", "{}", "hash3", "1762531570", True)
    ]
    self.db.insertInstanceList(instance_rows)
    result = self.db.getInstanceList(invalid_only=True)
    references = {r["reference"] for r in result}
    self.assertEqual(references, {"ref2"})

  def test_getInstanceList_both_filters_none(self):
    """Test getInstanceList with both valid_only and invalid_only set to None uses default behavior."""
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False)
    ]
    self.db.insertInstanceList(instance_rows)
    result = self.db.getInstanceList(valid_only=None, invalid_only=None)
    references = {r["reference"] for r in result}
    self.assertEqual(references, {"ref1", "ref2"})

  def test_getInstanceList_both_filters_true(self):
    """Test getInstanceList with both valid_only and invalid_only set to True uses default behavior."""
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True),
      ("ref2", "{}", "{}", "hash2", "1762531560", False)
    ]
    self.db.insertInstanceList(instance_rows)
    # When both are True, the elif condition fails, so it uses default behavior
    result = self.db.getInstanceList(valid_only=True, invalid_only=True)
    references = {r["reference"] for r in result}
    self.assertEqual(references, {"ref1", "ref2"})

  def test_getInstanceList_valid_only_with_custom_select(self):
    """Test getInstanceList with valid_only and custom select columns."""
    instance_rows = [
      ("ref1", '{"name": "test1"}', "{}", "hash1", "1762531540", True),
      ("ref2", '{"name": "test2"}', "{}", "hash2", "1762531560", False),
      ("ref3", '{"name": "test3"}', "{}", "hash3", "1762531570", True)
    ]
    self.db.insertInstanceList(instance_rows)
    result = self.db.getInstanceList("reference, json_parameters", valid_only=True)
    refs = {r["reference"] for r in result}
    self.assertEqual(refs, {"ref1", "ref3"})
    # Verify json_parameters is included
    for row in result:
      self.assertIn("json_parameters", row.keys())

  def test_getInstance_nonexistent(self):
    """Test getInstance with non-existent reference returns None."""
    result = self.db.getInstance("nonexistent_ref")
    self.assertIsNone(result)

  def test_removeInstanceList_empty_list(self):
    """Test removeInstanceList with empty list does nothing."""
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True)
    ]
    self.db.insertInstanceList(instance_rows)
    # Should not raise error
    self.db.removeInstanceList([])
    result = self.db.getInstanceList()
    self.assertEqual(len(result), 1)

  def test_updateInstanceList_empty_list(self):
    """Test updateInstanceList with empty list does nothing."""
    instance_rows = [
      ("ref1", "{}", "{}", "hash1", "1762531540", True)
    ]
    self.db.insertInstanceList(instance_rows)
    # Should not raise error
    update_query = "UPDATE instance SET json_parameters = ? WHERE reference = ?"
    self.db.updateInstanceList(update_query, [])
    result = self.db.getInstance("ref1")
    self.assertEqual(result["json_parameters"], "{}")

class TestInstanceListComparator(unittest.TestCase):
  """Unit tests for InstanceListComparator class"""

  def setUp(self):
    """Set up test fixtures before each test method"""
    # Sample update list
    self.update_list = [
      {"parameters": {"name": "test1", "value": 10}, "reference": "_test1"},
      {"parameters": {"name": "test2", "value": 20}, "reference": "_test2"},
      {"parameters": {"name": "test3", "value": 30}, "reference": "_test3"}
    ]

    # Sample stored dict with pre-computed hashes
    self.stored_dict = {
      "_test1": self._compute_hash({"name": "test1", "value": 10}),
      "_test2": self._compute_hash({"name": "test2", "value": 999}),  # Modified
      "_test4": self._compute_hash({"name": "test4", "value": 40})  # Removed
    }

  def _compute_hash(self, parameters):
    """Helper method to compute hash of parameters only"""
    obj_str = json.dumps(parameters, sort_keys=True)
    return hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

  def test_getNewInstancesList(self):
    """Test detection of new instances"""
    comparator = InstanceListComparator(self.update_list, self.stored_dict)
    added = comparator.getNewInstancesList()

    self.assertEqual(added, ["_test3"])

  def test_getDestroyedInstanceList(self):
    """Test detection of removed instances"""
    comparator = InstanceListComparator(self.update_list, self.stored_dict)
    removed = comparator.getDestroyedInstanceList()

    self.assertEqual(removed, ["_test4"])

  def test_getModifiedInstanceList(self):
    """Test detection of modified instances"""
    comparator = InstanceListComparator(self.update_list, self.stored_dict)
    modified = comparator.getModifiedInstanceList()

    self.assertIsInstance(modified, list)
    self.assertEqual(set(modified), {"_test2"})

  def test_compare_all_differences(self):
    """Test complete comparison returning all differences"""
    comparator = InstanceListComparator(self.update_list, self.stored_dict)
    result = comparator.compare()

    self.assertIn('added', result)
    self.assertIn('removed', result)
    self.assertIn('modified', result)

    self.assertEqual(result['added'], ["_test3"])
    self.assertEqual(result['removed'], ["_test4"])
    self.assertEqual(set(result['modified']), set(["_test2"]))

  def test_empty_update_list(self):
    """Test with empty update list"""
    comparator = InstanceListComparator([], self.stored_dict)
    result = comparator.compare()

    self.assertEqual(result['added'], [])
    self.assertEqual(set(result['removed']), set(["_test1", "_test2", "_test4"]))
    self.assertEqual(result['modified'], [])

  def test_empty_stored_dict(self):
    """Test with empty stored dictionary"""
    comparator = InstanceListComparator(self.update_list, {})
    result = comparator.compare()

    self.assertEqual(set(result['added']), set(["_test1", "_test2", "_test3"]))
    self.assertEqual(result['removed'], [])
    self.assertEqual(result['modified'], [])

  def test_no_changes(self):
    """Test when lists are identical"""
    update_list = [
      {"parameters": {"name": "test1", "value": 10}, "reference": "_test1"}
    ]
    stored_dict = {
      "_test1": self._compute_hash({"name": "test1", "value": 10})
    }

    comparator = InstanceListComparator(update_list, stored_dict)
    result = comparator.compare()

    self.assertEqual(result['added'], [])
    self.assertEqual(result['removed'], [])
    self.assertEqual(result['modified'], [])

  def test_hash_consistency(self):
    """Test that same instance produces same hash"""
    instance = {"parameters": {"name": "test", "value": 42}, "reference": "_ref"}

    comparator1 = InstanceListComparator([instance], {})
    comparator2 = InstanceListComparator([instance], {})

    self.assertEqual(
      comparator1.update_dict["_ref"],
      comparator2.update_dict["_ref"]
    )

  def test_nested_parameters(self):
    """Test with nested parameter structures"""
    update_list = [
      {
        "parameters": {
          "config": {"nested": {"deep": "value"}},
          "list": [1, 2, 3]
        },
        "reference": "_nested"
      }
    ]
    stored_dict = {}

    comparator = InstanceListComparator(update_list, stored_dict)
    result = comparator.compare()

    self.assertEqual(result['added'], ["_nested"])


class TestInstanceListComparatorPerformance(unittest.TestCase):
  """Performance tests for large datasets"""

  def test_large_dataset_objects(self):
    """Test with a lot of objects for performance"""
    quantity = 10000
    print("\n" + "="*70)
    print("PERFORMANCE TEST: %s objects" % quantity)
    print("="*70)

    # Generate instances
    start_generation = time.time()
    update_list = []
    for i in range(quantity):
      update_list.append({
        "parameters": {
          "name": "instance_{0}".format(i),
          "value": i,
          "data": "data_string_{0}".format(i % 100)
        },
        "reference": "_ref_{0}".format(i)
      })
    generation_time = time.time() - start_generation
    print("Generated {0} instances in {1:.2f}s".format(quantity, generation_time))

    # Create stored dict with:
    unchanged = 9000
    modified = 500
    destroyed = 500
    new = 500
    start_stored = time.time()
    stored_dict = {}

    # Add unchanged instances
    # Hash is computed only from parameters, not from reference
    for i in range(unchanged):
      obj_str = json.dumps(update_list[i]["parameters"], sort_keys=True, ensure_ascii=False)
      stored_dict["_ref_{0}".format(i)] = hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

    # Add modified instances
    for i in range(unchanged, unchanged+modified):
      modified_parameters = {
        "name": "instance_{0}".format(i),
        "value": i + 99999,  # Different value
        "data": "data_string_{0}".format(i % 100)
      }
      obj_str = json.dumps(modified_parameters, sort_keys=True, ensure_ascii=False)
      stored_dict["_ref_{0}".format(i)] = hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

    # Destroy instances
    for i in range(quantity, quantity + new):
      removed_parameters = {
        "name": "instance_{0}".format(i),
        "value": i,
        "data": "data_string_{0}".format(i % 100)
      }
      obj_str = json.dumps(removed_parameters, sort_keys=True, ensure_ascii=False)
      stored_dict["_ref_{0}".format(i)] = hashlib.sha256(obj_str.encode('utf-8')).hexdigest()

    stored_creation_time = time.time() - start_stored
    print("Created stored dict with {0} entries in {1:.2f}s".format(quantity, stored_creation_time))

    # Initialize comparator
    start_init = time.time()
    comparator = InstanceListComparator(update_list, stored_dict)
    init_time = time.time() - start_init
    print("Initialized comparator in {0:.2f}s".format(init_time))

    # Run comparison
    start_compare = time.time()
    result = comparator.compare()
    compare_time = time.time() - start_compare
    print("Completed comparison in {0:.2f}s".format(compare_time))

    # Validate results
    print("\nResults:")
    print("  - Added instances: {0}".format(len(result['added'])))
    print("  - Removed instances: {0}".format(len(result['removed'])))
    print("  - Modified instances: {0}".format(len(result['modified'])))

    self.assertEqual(len(result['added']), new, "Should have %d new instances" % new)
    self.assertEqual(len(result['removed']), destroyed, "Should have %d removed instances" % destroyed)
    self.assertEqual(len(result['modified']), modified, "Should have %d modified instances" % modified)

    total_time = generation_time + stored_creation_time + init_time + compare_time
    print("\nTotal execution time: {0:.2f}s".format(total_time))
    print("="*70 + "\n")

    # Performance assertion (should complete in reasonable time)
    self.assertLess(compare_time, 1, "Comparison should complete in less than 1 seconds")


class TestSharedInstanceResultDB(unittest.TestCase):
  """Unit tests for SharedInstanceResultDB class"""

  def setUp(self):
    self.db_fd, self.db_path = tempfile.mkstemp()
    self.db = SharedInstanceResultDB(self.db_path)

  def tearDown(self):
    os.close(self.db_fd)
    os.unlink(self.db_path)

  def test_json_error_cleared_for_valid_instances(self):
    """Test that json_error is cleared for valid instances when updated."""
    # Insert initial instance with both json_parameters and json_error (invalid)
    initial_error = {"message": "Error message", "errors": ["Error 1"]}
    initial_params = {"name": "test1", "value": 10}

    # Manually insert an instance with error info
    instance_row = (
      "ref1",
      json.dumps(initial_params, sort_keys=True),
      json.dumps(initial_error, sort_keys=True),
      "initial_hash",
      str(int(time.time())),
      False  # Invalid
    )
    self.db.insertInstanceList([instance_row])

    # Verify initial state
    instance = self.db.getInstance("ref1")
    self.assertEqual(json.loads(instance["json_parameters"]), initial_params)
    self.assertEqual(json.loads(instance["json_error"]), initial_error)

    # Update with new json_parameters using updateFromValidationResults (now valid)
    new_params = {"name": "test1", "value": 20}  # Changed value
    valid_list = [{"reference": "ref1", "parameters": new_params}]
    invalid_list = []

    self.db.updateFromValidationResults(valid_list, invalid_list)

    # Verify that json_parameters was updated
    updated_instance = self.db.getInstance("ref1")
    self.assertEqual(json.loads(updated_instance["json_parameters"]), new_params)

    # Verify that json_error was cleared for valid instance
    self.assertEqual(
      json.loads(updated_instance["json_error"]),
      {},
      "json_error should be empty for valid instances"
    )

  def test_getStoredDict(self):
    """Test getStoredDict returns correct mapping of reference to hash."""
    # Insert instances
    params1 = {"name": "test1"}
    params2 = {"name": "test2"}
    # Hash is computed only from parameters, not from reference
    hash1 = hashlib.sha256(json.dumps(params1, sort_keys=True).encode('utf-8')).hexdigest()
    hash2 = hashlib.sha256(json.dumps(params2, sort_keys=True).encode('utf-8')).hexdigest()

    instance_rows = [
      ("ref1", json.dumps(params1), "{}", hash1, str(int(time.time())), True),
      ("ref2", json.dumps(params2), "{}", hash2, str(int(time.time())), False)
    ]
    self.db.insertInstanceList(instance_rows)

    stored_dict = self.db.getStoredDict()
    self.assertEqual(stored_dict["ref1"], hash1)
    self.assertEqual(stored_dict["ref2"], hash2)
    self.assertEqual(len(stored_dict), 2)

  def test_updateFromValidationResults_add_new_instances(self):
    """Test updateFromValidationResults adds new instances correctly."""
    valid_list = [
      {"reference": "ref1", "parameters": {"name": "test1"}},
      {"reference": "ref2", "parameters": {"name": "test2"}}
    ]
    invalid_list = [
      {"reference": "ref3", "parameters": {"name": "test3"}}
    ]

    self.db.updateFromValidationResults(valid_list, invalid_list)

    # Verify all instances were added
    all_instances = self.db.getInstanceList()
    refs = {r["reference"] for r in all_instances}
    self.assertEqual(refs, {"ref1", "ref2", "ref3"})

    # Verify valid_parameter is set correctly
    ref1 = self.db.getInstance("ref1")
    ref2 = self.db.getInstance("ref2")
    ref3 = self.db.getInstance("ref3")
    self.assertTrue(ref1["valid_parameter"])
    self.assertTrue(ref2["valid_parameter"])
    self.assertFalse(ref3["valid_parameter"])

  def test_updateFromValidationResults_remove_instances(self):
    """Test updateFromValidationResults removes instances that are no longer in the list."""
    # First, add some instances
    valid_list1 = [
      {"reference": "ref1", "parameters": {"name": "test1"}},
      {"reference": "ref2", "parameters": {"name": "test2"}},
      {"reference": "ref3", "parameters": {"name": "test3"}}
    ]
    self.db.updateFromValidationResults(valid_list1, [])

    # Now update with fewer instances - ref2 and ref3 should be removed
    valid_list2 = [
      {"reference": "ref1", "parameters": {"name": "test1"}}
    ]
    self.db.updateFromValidationResults(valid_list2, [])

    # Verify only ref1 remains
    all_instances = self.db.getInstanceList()
    refs = {r["reference"] for r in all_instances}
    self.assertEqual(refs, {"ref1"})

  def test_updateFromValidationResults_modify_instances(self):
    """Test updateFromValidationResults updates modified instances."""
    # Add initial instance
    valid_list1 = [
      {"reference": "ref1", "parameters": {"name": "test1", "value": 10}}
    ]
    self.db.updateFromValidationResults(valid_list1, [])

    # Get initial hash
    initial_instance = self.db.getInstance("ref1")
    initial_hash = initial_instance["hash"]

    # Update with modified parameters
    valid_list2 = [
      {"reference": "ref1", "parameters": {"name": "test1", "value": 20}}
    ]
    self.db.updateFromValidationResults(valid_list2, [])

    # Verify parameters were updated
    updated_instance = self.db.getInstance("ref1")
    self.assertEqual(json.loads(updated_instance["json_parameters"])["value"], 20)
    # Hash should have changed
    self.assertNotEqual(updated_instance["hash"], initial_hash)

  def test_updateFromValidationResults_change_valid_status(self):
    """Test updateFromValidationResults changes valid_parameter status when instance moves between valid and invalid."""
    # Add as valid instance
    valid_list1 = [
      {"reference": "ref1", "parameters": {"name": "test1"}}
    ]
    self.db.updateFromValidationResults(valid_list1, [])

    instance = self.db.getInstance("ref1")
    self.assertTrue(instance["valid_parameter"])

    # Move to invalid
    invalid_list = [
      {"reference": "ref1", "parameters": {"name": 2}}
    ]
    self.db.updateFromValidationResults([], invalid_list)

    instance = self.db.getInstance("ref1")
    self.assertFalse(instance["valid_parameter"])

    # Move back to valid
    valid_list2 = [
      {"reference": "ref1", "parameters": {"name": "test1"}}
    ]
    self.db.updateFromValidationResults(valid_list2, [])

    instance = self.db.getInstance("ref1")
    self.assertTrue(instance["valid_parameter"])

  def test_updateFromValidationResults_empty_lists(self):
    """Test updateFromValidationResults with empty lists preserves existing data.

    This test verifies the fix: when both lists are empty, existing data is preserved
    to avoid unintended deletion of all historical data.
    """
    # Add some instances
    valid_list1 = [
      {"reference": "ref1", "parameters": {"name": "test1"}},
      {"reference": "ref2", "parameters": {"name": "test2"}}
    ]
    self.db.updateFromValidationResults(valid_list1, [])

    # Update with empty lists - data should be preserved (not deleted)
    self.db.updateFromValidationResults([], [])

    # Verify all instances are still present (not removed)
    all_instances = self.db.getInstanceList()
    self.assertEqual(len(all_instances), 2,
                     "Instances should be preserved when both lists are empty")

  def test_updateFromValidationResults_empty_lists_preserves_data(self):
    """Test that updateFromValidationResults with both empty lists preserves existing data.

    This test verifies the fix for the bug where calling updateFromValidationResults
    with both empty valid_list and invalid_list would create an empty update_list,
    causing InstanceListComparator to treat all stored instances as "removed",
    leading to unintended deletion of all historical data.

    The fix adds an early return when both lists are empty to prevent this.
    """
    # Add some instances to the database
    valid_list1 = [
      {"reference": "ref1", "parameters": {"name": "test1"}},
      {"reference": "ref2", "parameters": {"name": "test2"}}
    ]
    self.db.updateFromValidationResults(valid_list1, [])

    # Verify instances are in the database
    all_instances_before = self.db.getInstanceList('reference, json_parameters, json_error, hash, valid_parameter')
    self.assertEqual(len(all_instances_before), 2)
    refs_before = {r["reference"] for r in all_instances_before}
    self.assertEqual(refs_before, {"ref1", "ref2"})

    # Call updateFromValidationResults with both lists empty
    # This should NOT delete all instances (fix prevents deletion)
    self.db.updateFromValidationResults([], [])

    # Verify instances are still in the database (not deleted)
    all_instances_after = self.db.getInstanceList('reference, json_parameters, json_error, hash, valid_parameter')
    self.assertEqual(len(all_instances_after), 2,
                     "Instances should be preserved when both lists are empty")
    refs_after = {r["reference"] for r in all_instances_after}
    self.assertEqual(refs_after, {"ref1", "ref2"})

    # Verify the data is unchanged
    ref1_before_list = [r for r in all_instances_before if r["reference"] == "ref1"]
    ref1_after_list = [r for r in all_instances_after if r["reference"] == "ref1"]
    self.assertEqual(len(ref1_before_list), 1, "ref1 should exist before")
    self.assertEqual(len(ref1_after_list), 1, "ref1 should exist after")

    ref1_before = ref1_before_list[0]
    ref1_after = ref1_after_list[0]
    self.assertEqual(ref1_before["json_parameters"], ref1_after["json_parameters"])
    self.assertEqual(ref1_before["hash"], ref1_after["hash"])

  def test_updateFromValidationResults_mixed_scenario(self):
    """Test updateFromValidationResults with a complex mixed scenario."""
    # Initial state: 3 instances
    valid_list1 = [
      {"reference": "ref1", "parameters": {"name": "test1"}},
      {"reference": "ref2", "parameters": {"name": "test2"}},
      {"reference": "ref3", "parameters": {"name": "test3"}}
    ]
    self.db.updateFromValidationResults(valid_list1, [])

    # Update: ref1 modified, ref2 removed, ref3 stays same, ref4 added, ref5 added as invalid
    valid_list2 = [
      {"reference": "ref1", "parameters": {"name": "test1", "updated": True}},
      {"reference": "ref3", "parameters": {"name": "test3"}},
      {"reference": "ref4", "parameters": {"name": "test4"}}
    ]
    invalid_list2 = [
      {"reference": "ref5", "parameters": {"name": "test5"}}
    ]
    self.db.updateFromValidationResults(valid_list2, invalid_list2)

    # Verify final state
    all_instances = self.db.getInstanceList()
    refs = {r["reference"] for r in all_instances}
    self.assertEqual(refs, {"ref1", "ref3", "ref4", "ref5"})

    # Verify ref1 was modified
    ref1 = self.db.getInstance("ref1")
    self.assertTrue(json.loads(ref1["json_parameters"]).get("updated"))

    # Verify ref3 unchanged (same hash)
    ref3 = self.db.getInstance("ref3")
    self.assertEqual(json.loads(ref3["json_parameters"])["name"], "test3")

    # Verify ref4 added as valid
    ref4 = self.db.getInstance("ref4")
    self.assertTrue(ref4["valid_parameter"])

    # Verify ref5 added as invalid
    ref5 = self.db.getInstance("ref5")
    self.assertFalse(ref5["valid_parameter"])
