#!/usr/bin/env python

# Parse Ansible result log file and and generate a report

import os, time
import json
import sqlite3
from datetime import datetime, timedelta

import sys

FIELDS = ['cmd', 'command', 'start', 'end', 'delta', 'msg', 'stdout', 'stderr',
          'response', 'status_code', 'url', 'dest']

class ansibleReport(object):

  def __init__(self, db_path,
                    ansible_log_dir,
                    name):
    self.db_path = db_path
    self.ansible_log_dir = ansible_log_dir
    self.name = name
    self.result_OK = '127.0.0.1_OK'
    self.result_failed = '127.0.0.1_FAILED'
    self.result_failed_ignore = '127.0.0.1_FAILED_INGORED' # tipo in ansible log upload pluging
    self.date_format = '%Y-%m-%d %H:%M:%S'
    self.day_format = '%Y-%m-%d'
    
    self._init_db()

  def _init_db(self):
    db = sqlite3.connect(self.db_path)
    c = db.cursor()
    c.executescript("""
CREATE TABLE IF NOT EXISTS ansible_report (
  name VARCHAR(40),
  reportdate VARCHAR(15),
  createdate VARCHAR(15),
  status VARCHAR(20),
  success_count INTEGER,
  ignored_count INTEGER,
  failed_count INTEGER,
  ignored TEXT,
  failed TEXT,
  success TEXT);
""")
    db.commit()
    db.close()

  def connect_db(self):
    db = sqlite3.connect(self.db_path)
    return db

  def insertEntryDb(self, table_name, data_dict):
    db = self.connect_db()
    columns = data_dict.keys()
    entries = ', '.join(columns)
    values = '?' + ', ?' * (len(columns)-1)
    sql_string = "insert into %s(%s) values (%s)" % (
                    table_name, entries, values)
    tuple_data = ()
    for key in columns:
      tuple_data += (data_dict[key],)
    db.execute(sql_string, tuple_data)
    db.commit()
    db.close()

  def selectEntriesDb(self, fields=[], start_date=None, limit=0, success=None, order='DESC', where=""):
    db = self.connect_db()

    entries = ', '.join(fields) if fields else '*'
    query = "select %s from ansible_report " % entries
    where = " and %s" % where if where else ""
    if not start_date:
      start_date = datetime.utcnow().strftime(self.day_format)
    tuple_values = (start_date,)
    if success is not None:
      status = 'OK' if success else 'FAILLED'
      query += "where createdate>=? and status=? %s order by createdate %s" % (where, order)
      tuple_values += (status,)
    else:
      query += "where createdate>=? %s order by createdate %s" % (where, order)
    if limit:
      query += " limit ?"
      tuple_values += (limit,)

    rows = db.cursor().execute(query, tuple_values)
    #db.close()
    if rows:
      return [list(row) for row in rows]
    return []

  def truncateEntriesDb(self, table_name, on_field, to_value, operator='<'):
    db = self.connect_db()
    query = "delete from %s where %s%s?" % (table_name, on_field,
                                            operator)
    db.execute(query, (to_value,))
    db.commit()
    db.close()

  def getLogString(self, res, head=False):
    log = ""
    if type(res) == type(dict()):
      log = '%s, args [%s]\n' % (res['invocation']['module_name'],
                                        res['invocation']['module_args'])
      if head:
        return log
      for field in FIELDS:
        if field in res.keys():
        	# use default encoding, check out sys.setdefaultencoding
          log += '\n{0}:\n{1}'.format(field, res[field])
  
    return log

  def _read_file(self, filepath):
    content = '[]'
    with open(filepath, 'r') as f:
      content = f.read()
    return content

  def saveResult(self):
    
    date = datetime.utcnow().strftime(self.date_format)

    files_list = os.listdir(self.ansible_log_dir)
    if not len(files_list):
      return

    to_date = (datetime.now() - timedelta(days=2)).strftime(self.date_format)
    cmp_file = os.path.join(self.ansible_log_dir, files_list.pop())
    modification_date = datetime.fromtimestamp(
                            os.path.getmtime(cmp_file)
                          ).strftime(self.date_format)
    # Get the latest insert date
    result = self.selectEntriesDb(['reportdate'], start_date=to_date, limit=1)
    if len(result):
      latest_date = result[0][0]
      if latest_date >= modification_date:
        return

    file_map = dict(
          success_file=os.path.join(self.ansible_log_dir, self.result_OK),
          failed_file=os.path.join(self.ansible_log_dir, self.result_failed),
          ignored_file=os.path.join(self.ansible_log_dir, self.result_failed_ignore))
    
    data = dict(name=self.name, status='FAILED',
                reportdate=modification_date, createdate=date,
                success_count=0, ignored_count=0,
                failed_count=0, success="",
                failed="", ignored="")
    for category in ('failed', 'success', 'ignored'):
      file_category = file_map['%s_file' % category]
      if os.path.exists(file_category):
        text_content = self._read_file(file_category)
        count = len(json.loads(text_content))
        if count > 0:
          data['%s_count' % category] = count
          data[category] = text_content
    
    if data['failed_count'] == 0:
      data['status'] = 'OK'

    self.insertEntryDb('ansible_report', data)

  def getAnsibleReport(self, start_date=None, limit=0, success=None, order='DESC', category=None, head=False, only_state=True):
    """Get one or many entries from the ansible report table.
    """
    where = ""
    get_content = category is not None
    fields = ['name', 'reportdate', 'createdate', 'status', 'success_count',
                'ignored_count', 'failed_count']
    if category:
      where = " %s_count>0" % category
      if not only_state:
        fields.append(category)

    rows = self.selectEntriesDb(fields=fields, start_date=start_date,
                                limit=limit, success=success, order=order,
                                where=where)
    result_dict = {}
    if category and not only_state:
      last_pos = len(fields) -1
      for i in range (0, len(rows)):
        message = ""
        message_list = json.loads(rows[i][last_pos])
        for msg in message_list:
          message += '%s\n\n' %  self.getLogString(msg, head=head)
        rows[i][last_pos] = message
    else:
      return {}
    return rows


if __name__ == "__main__":
  json = """{
  "status": "OK",
  "message": "kvm-1: OK(114) FAILED(0) IGNORED(2)",
  "description": "Ansible playbook report in kvm-1. Execution date is: 2015-08-28 17:42:01."
}"""
  parameter_dict = json.loads(sys.argv[1])
  with open(parameter_dict['status_path'], 'w') as status_file:
    status_file.write(json)
  
  