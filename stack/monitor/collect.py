# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import sqlite3
import os
from time import strftime
from datetime import datetime, timedelta

class Database:

  def __init__(self, db_path = None):
    assert os.path.exists(db_path) and os.path.isfile(db_path)
    self.uri = db_path
    self.connection = None
    self.cursor = None

  def connect(self):
    self.connection = sqlite3.connect(self.uri)
    self.cursor = self.connection.cursor()

  def close(self):
    assert self.connection is not None
    self.cursor.close()
    self.connection.close()

  def _execute(self, sql):
    assert self.connection is not None
    return self.cursor.execute(sql)

  def select(self, table, date=None, columns="*", where=None):
    """ Query database for a full table information """
    if date is not None:
      where_clause = " WHERE date = '%s' " % date
    else:
      where_clause = ""
    
    if where is not None:
      if where_clause == "":
        where_clause += " WHERE 1 = 1 "
      where_clause += " AND %s " % where 
    select_sql = "SELECT %s FROM %s %s " % (columns, table, where_clause)
    return self._execute(select_sql)

  def getPartitionCPULoadAverage(self, partition_id, date_scope):
    self.connect()
    query_result_cursor = self.select("user", date_scope,
                       columns="SUM(cpu_percent)", 
                       where="partition = '%s'" % partition_id)

    cpu_percent_sum = zip(*query_result_cursor)
    if len(cpu_percent_sum) and cpu_percent_sum[0][0] is None:
      return

    query_result_cursor = self.select("user", date_scope,
                       columns="COUNT(DISTINCT time)", 
                       where="partition = '%s'" % partition_id)

    sample_amount = zip(*query_result_cursor)
    self.close()

    if len(sample_amount) and len(cpu_percent_sum):
      return round(cpu_percent_sum[0][0]/sample_amount[0][0], 2)

  def getPartitionUsedMemoryAverage(self, partition_id, date_scope):
    self.connect()
    query_result_cursor = self.select("user", date_scope,
                       columns="SUM(memory_rss)", 
                       where="partition = '%s'" % partition_id)

    memory_sum = zip(*query_result_cursor)
    if len(memory_sum) and memory_sum[0][0] is None:
      return

    query_result_cursor = self.select("user", date_scope,
                       columns="COUNT(DISTINCT time)", 
                       where="partition = '%s'" % partition_id)

    sample_amount = zip(*query_result_cursor)
    self.close()

    if len(sample_amount) and len(memory_sum):
      return round(memory_sum[0][0]/(sample_amount[0][0]*1024*1024.0), 2)

  def getPartitionConsumption(self, partition_id, where=""):
    self.connect()
    comsumption_list = []
    if where != "":
      where = "and %s" % where
    date_scope = datetime.now().strftime('%Y-%m-%d')
    min_time = (datetime.now() - timedelta(minutes=1)).strftime('%H:%M:00')
    max_time = (datetime.now() - timedelta(minutes=1)).strftime('%H:%M:59')
    sql_query = """select count(pid), SUM(cpu_percent) as cpu_result, SUM(cpu_time), 
MAX(cpu_num_threads), SUM(memory_percent), SUM(memory_rss), pid from user 
where date='%s' and partition='%s' and (time between '%s' and '%s') %s 
group by pid order by cpu_result desc""" % (
        date_scope, partition_id, min_time, max_time, where)
    query_result = self._execute(sql_query)
    for result in query_result:
      count = int(result[0])
      if not count > 0:
        continue
      comsumption_list.append([result[6], round((result[1]/count), 2),
                    round((result[2]/count), 2),
                    round(result[3], 2), round((result[4]/count), 2),
                    round((result[5]/(count*1024*1024.0)), 2)])
    self.close()
    return comsumption_list
  
  def getPartitionComsumptionStatus(self, partition_id, where=""):
    self.connect()
    if where != "":
      where = " and %s" % where
    date_scope = datetime.now().strftime('%Y-%m-%d')
    min_time = (datetime.now() - timedelta(minutes=1)).strftime('%H:%M:00')
    max_time = (datetime.now() - timedelta(minutes=1)).strftime('%H:%M:59')
    sql_query = """select count(pid), SUM(cpu_percent), SUM(cpu_time), 
SUM(cpu_num_threads), SUM(memory_percent), SUM(memory_rss) from user where 
date='%s' and partition='%s' and (time between '%s' and '%s') %s""" % (
        date_scope, partition_id, min_time, max_time, where)
    query_result = self._execute(sql_query)
    result_list = zip(*query_result)
    self.close()
    
    if len(result_list):
      result = result_list #[0]
      return {'total_process': result[0][0],
            'cpu_percent': round(result[1][0], 2),
            'cpu_time': round(result[2][0], 2),
            'cpu_num_threads': round(result[3][0], 2),
            'memory_percent': round(result[4][0], 2),
            'memory_rss': round(result[5][0]/(1024*1024.0), 2)}
            
    return None
