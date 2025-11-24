import hashlib
import json
import sqlite3
import time

class LocalDBAccessor(object):

  def __init__(self, db_path, schema):
    self.db_path = db_path
    self._createDatabaseIfNeeded(schema)

  def _connectDB(self):
    con = sqlite3.connect(self.db_path, timeout=30.0)
    con.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency (readers don't block writers)
    # WAL mode may not be available in all configurations, so we ignore errors
    try:
      con.execute('PRAGMA journal_mode=WAL')
    except Exception:
      # WAL mode not available, continue with default mode
      pass
    return con

  def _createDatabaseIfNeeded(self, schema):
    """
    Analyses current database compared to defined schema,
    and adapt tables/data it if needed.
    """
    con = self._connectDB()
    con.execute('BEGIN')
    try:
      con.executescript(schema)
    except Exception:
      con.rollback()
      con.close()
      raise
    con.commit()
    con.close()

  def execute_query(self, connection, query, args=()):
    try:
      with connection:
        cur = connection.execute(query, args)
        return cur
    except Exception as exc:
      connection.close()
      raise ValueError(
          "There was an issue processing query %r with args %r: %s"
          % (query, args, exc)
      )

  def execute(self, query, args=()):
    connection = self._connectDB()
    cur = self.execute_query(connection, query, args)
    cur.close()
    connection.close()

  def fetchAll(self, query, args=()):
    connection = self._connectDB()
    cur = self.execute_query(connection, query, args)
    result = cur.fetchall()
    cur.close()
    connection.close()
    return result

  def fetchOne(self, query, args=()):
    connection = self._connectDB()
    cur = self.execute_query(connection, query, args)
    result = cur.fetchone()
    cur.close()
    connection.close()
    return result

  def insertMany(self, query, rows, connection=None, commit=True):
    """
    Bulk insert rows.

    Arguments:
    - query: SQL INSERT query string with placeholders
    - rows: list of parameter tuples for each row insert
    - connection: optional existing database connection to use
    - commit: whether to commit the transaction (default True)
    """
    should_close = connection is None
    if connection is None:
      connection = self._connectDB()
    try:
      cursor = connection.cursor()
      cursor.executemany(query, rows)
      if commit:
        connection.commit()
    except Exception as exc:
      if commit:
        connection.rollback()
      raise ValueError("Bulk insert failed: %s" % exc)
    finally:
      cursor.close()
      if should_close:
        connection.close()

  def removeMany(self, query, keys, connection=None, commit=True):
    """
    Remove many rows matching keys.

    Arguments:
    - query: SQL DELETE query string with a single placeholder for IN clause, e.g.
      "DELETE FROM table WHERE id IN ({})"
    - keys: iterable of keys (e.g., IDs) to delete
    - connection: optional existing database connection to use
    - commit: whether to commit the transaction (default True)

    Note: SQLite has a default limit of 999 parameters. This method batches
    deletes if the number of keys exceeds this limit.
    """
    if not keys:
      return  # Nothing to delete

    # SQLite default parameter limit is 999, use 900 to be safe
    MAX_PARAMS = 900
    keys_list = list(keys)

    should_close = connection is None
    if connection is None:
      connection = self._connectDB()
    try:
      # Batch deletes if we exceed the parameter limit
      for i in range(0, len(keys_list), MAX_PARAMS):
        batch = keys_list[i:i + MAX_PARAMS]
        placeholders = ','.join('?' for _ in batch)
        sql = query.format(placeholders)
        connection.execute(sql, batch)
      if commit:
        connection.commit()
    except Exception as exc:
      if commit:
        connection.rollback()
      raise ValueError("Bulk delete failed: %s" % exc)
    finally:
      if should_close:
        connection.close()

  def updateMany(self, query, params_list, connection=None, commit=True):
    """
    Bulk update rows.

    Arguments:
    - query: SQL UPDATE query string with placeholders, e.g.
      "UPDATE table SET col1 = ?, col2 = ? WHERE id = ?"
    - params_list: list (or iterable) of parameter tuples for each row update.
      Each tuple matches the placeholders in the query in order.
    - connection: optional existing database connection to use
    - commit: whether to commit the transaction (default True)
    """
    should_close = connection is None
    if connection is None:
      connection = self._connectDB()
    try:
      cursor = connection.cursor()
      cursor.executemany(query, params_list)
      if commit:
        connection.commit()
    except Exception as exc:
      if commit:
        connection.rollback()
      raise ValueError("Bulk update failed: %s" % exc)
    finally:
      cursor.close()
      if should_close:
        connection.close()

class HostedInstanceLocalDB(object):
  schema = """CREATE TABLE IF NOT EXISTS instance (
    reference VARCHAR(255), -- unique instance reference
    json_parameters TEXT,
    json_error TEXT,
    hash VARCHAR(255),
    timestamp VARCHAR(255),
    valid_parameter BOOLEAN,
    PRIMARY KEY (reference)
    );
    CREATE INDEX IF NOT EXISTS idx_reference ON instance(reference);
    CREATE INDEX IF NOT EXISTS idx_valid_parameter ON instance(valid_parameter);
    CREATE INDEX IF NOT EXISTS idx_hash ON instance(hash);"""

  def __init__(self, db_path):
    self.db = LocalDBAccessor(db_path, self.schema)

  def getInstanceList(self, select_tuple_string="reference", valid_only=None, invalid_only=None):
    # Note: select_tuple_string should only contain valid column names
    # from the instance table. This is safe as it's only used internally
    # with known column names (e.g., "reference", "hash", "reference, hash").
    if valid_only and not invalid_only:
      return self.db.fetchAll(
        "select %s from instance where valid_parameter = ?" % select_tuple_string,
        (True,)
      )
    elif invalid_only and not valid_only:
      return self.db.fetchAll(
        "select %s from instance where valid_parameter = ?" % select_tuple_string,
        (False,)
      )
    else:
      return self.db.fetchAll(
        "select %s from instance" % select_tuple_string
      )

  def insertInstanceList(self, instance_list, connection=None, commit=True):
    self.db.insertMany(
      "INSERT INTO instance (reference, json_parameters, json_error, hash, timestamp, valid_parameter) VALUES (?, ?, ?, ?, ?, ?)",
      instance_list,
      connection=connection,
      commit=commit)

  def getInstance(self, reference):
    return self.db.fetchOne(
      "SELECT * FROM instance WHERE reference=?", (reference,)
    )

  def removeInstanceList(self, reference_list, connection=None, commit=True):
    self.db.removeMany(
      "DELETE FROM instance WHERE reference IN ({})",
      reference_list,
      connection=connection,
      commit=commit
    )

  def updateInstanceList(self, update_query, instance_list_tuple, connection=None, commit=True):
    self.db.updateMany(update_query, instance_list_tuple, connection=connection, commit=commit)


class InstanceListComparator(object):
  """
  Class used to compare list of instances A update list and B stored_list and provide:
  * the new elements in A
  * elements removed from A compared to B
  * elements in A changed compared to B

  the stored list is a dict with key as instance reference and value as hash
  the source list is a list of instance with the following structure
  instance_list = [
      {"parameters": { ... }, "reference": "_sharedtest1"},
      {"parameters": { ... }, "reference": "_sharedtest2"}
  ]
  """

  def __init__(self, update_list, stored_dict):
    self.update_list = update_list
    self.update_dict = {}
    self.stored_dict = stored_dict
    self.updateHashDict()
    self.update_instance_set = set(self.update_dict.keys())
    self.stored_instance_set = set(self.stored_dict.keys())

  def updateHashDict(self):
    for instance in self.update_list:
      # Use sort_keys=True for deterministic key order
      obj_str = json.dumps(instance, sort_keys=True)
      obj_hash = hashlib.sha256(obj_str.encode('utf-8')).hexdigest()
      self.update_dict[instance["reference"]] = obj_hash

  def getNewInstancesList(self):
    return list(self.update_instance_set - self.stored_instance_set)

  def getDestroyedInstanceList(self):
    """
    Get elements that are in stored_dict but not in update_dict.
    """
    return list(self.stored_instance_set - self.update_instance_set)

  def getModifiedInstanceList(self):
    """
    Get elements with the same keys but different values.
    """
    common_keys = self.stored_instance_set & self.update_instance_set
    return [k
        for k, v in self.update_dict.items()
        if k in self.stored_dict and self.stored_dict[k] != v]

  def compare(self):
    """
    Perform complete comparison and return all differences.
    """
    return {
        'added': self.getNewInstancesList(),
        'removed': self.getDestroyedInstanceList(),
        'modified': self.getModifiedInstanceList()
    }

class SharedInstanceResultDB(HostedInstanceLocalDB):
  """
  Database for storing shared instance validation results.
  Inherits from HostedInstanceLocalDB and uses InstanceListComparator
  to efficiently update the database with validation results.
  """
  def __init__(self, db_path):
    super(SharedInstanceResultDB, self).__init__(db_path)

  def getStoredDict(self):
    """
    Get current stored instances as a dict mapping reference to hash.
    Returns dict with reference as key and hash as value.
    """
    stored_list = self.getInstanceList("reference, hash")
    return {row["reference"]: row["hash"] for row in stored_list}

  def updateFromValidationResults(self, valid_list, invalid_list):
    """
    Update database with validation results using InstanceListComparator
    to detect changes and efficiently update only what's needed.

    All database operations are performed in a single transaction for
    better performance and atomicity.

    Args:
      valid_list: List of dicts with 'reference' and 'parameters' keys
      invalid_list: List of dicts with 'reference' and 'parameters' keys
    """
    # Combine valid and invalid into update list (optimize list building)
    update_list = [
      {"parameters": item["parameters"], "reference": item["reference"]}
      for item in valid_list
    ]
    update_list.extend([
      {"parameters": item["parameters"], "reference": item["reference"]}
      for item in invalid_list
    ])

    # Get current stored state
    stored_dict = self.getStoredDict()

    # Use comparator to find changes
    comparator = InstanceListComparator(update_list, stored_dict)
    comparison = comparator.compare()

    # Reuse computed hashes from comparator to avoid recomputation
    # Note: comparator.update_dict already has the hashes we need
    computed_hashes = comparator.update_dict

    # Prepare data for insert/update
    # Create a mapping of reference to (parameters, valid_parameter, error_info)
    instance_map = {}
    for item in valid_list:
      instance_map[item["reference"]] = (item["parameters"], True, {})  # Empty error_info for valid
    for item in invalid_list:
      errors = item.get("errors", [])
      error_info = {}
      if errors:
        error_info = {
          "message": "; ".join(errors),
          "errors": errors
        }
      instance_map[item["reference"]] = (item["parameters"], False, error_info)

    # Perform all operations in a single transaction using existing methods
    connection = self.db._connectDB()
    timestamp = str(int(time.time()))
    try:
      # Remove destroyed instances using existing method
      if comparison["removed"]:
        self.removeInstanceList(comparison["removed"], connection=connection, commit=False)

      # Insert new instances using existing method
      new_instance_reference_list = comparison["added"]
      if new_instance_reference_list:
        new_instance_list = []
        for instance_reference in new_instance_reference_list:
          params, valid, error_info = instance_map[instance_reference]
          params_json = json.dumps(params, sort_keys=True)
          # Reuse hash from comparator
          instance_hash = computed_hashes[instance_reference]
          # For valid instances, json_error should always be empty
          # For invalid instances, use the error information (validation errors)
          if valid:
            error_json = "{}"
          else:
            error_json = json.dumps(error_info, sort_keys=True) if error_info else "{}"
          new_instance_list.append((instance_reference, params_json, error_json, instance_hash, timestamp, valid))
        if new_instance_list:
          self.insertInstanceList(new_instance_list, connection=connection, commit=False)

      # Update modified instances using existing method
      updated_instance_list = comparison["modified"]
      if updated_instance_list:
        update_instance_list = []
        for instance_reference in updated_instance_list:
          params, valid, error_info = instance_map[instance_reference]
          params_json = json.dumps(params, sort_keys=True)
          # Reuse hash from comparator
          instance_hash = computed_hashes[instance_reference]
          # For valid instances, json_error should always be empty
          # For invalid instances, use the error information (validation errors)
          if valid:
            error_json = "{}"
          else:
            error_json = json.dumps(error_info, sort_keys=True) if error_info else "{}"
          update_instance_list.append((params_json, error_json, instance_hash, timestamp, valid, instance_reference))
        if update_instance_list:
          update_query = "UPDATE instance SET json_parameters = ?, json_error = ?, hash = ?, timestamp = ?, valid_parameter = ? WHERE reference = ?"
          self.updateInstanceList(update_query, update_instance_list, connection=connection, commit=False)

      # Commit all changes at once
      connection.commit()
    except Exception as exc:
      connection.rollback()
      raise ValueError("Failed to update validation results: %s" % exc)
    finally:
      connection.close()
