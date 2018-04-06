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

import os
from time import strftime
import datetime

from slapos.util import sqlite_connect

class Database:

  database_name = "collector.db"
  table_list = ["user", "computer", "system", "disk", \
                 "temperature", "heating"]
  preserve_table_list = ["heating"]

  CREATE_USER_TABLE = "create table if not exists user " \
                        "(partition text, pid real, process text, " \
                        " cpu_percent real, cpu_time real, " \
                        " cpu_num_threads real,  memory_percent real, " \
                        " memory_rss real, io_rw_counter real, " \
                        " io_cycles_counter real, date text, time text, " \
                        " reported integer NULL DEFAULT 0)"

  CREATE_USER_PARTITION_DATE_TIME_INDEX = "CREATE INDEX IF NOT EXISTS user_partition_date_time ON"\
                                          " user (partition, date, time)"

  CREATE_FOLDER_TABLE = "create table if not exists folder "\
                          "(partition text, disk_used real, date text, " \
                          " time text, reported integer NULL DEFAULT 0)" 

  CREATE_COMPUTER_TABLE = "create table if not exists computer "\
                          "(cpu_num_core real, cpu_frequency real, cpu_type text," \
                          " memory_size real, memory_type text, partition_list text," \
                          " date text, time text, reported integer NULL DEFAULT 0)"


  CREATE_SYSTEM_TABLE = "create table if not exists system " \
                        "(loadavg real, cpu_percent real, memory_used real, "\
                        " memory_free real, net_in_bytes real, net_in_errors real, "\
                        " net_in_dropped real, net_out_bytes real, net_out_errors real, "\
                        " net_out_dropped real, date text, time text, " \
                        " reported integer NULL DEFAULT 0)"

  CREATE_DISK_PARTITION = "create table if not exists disk "\
                          "(partition text, used text, free text, mountpoint text, " \
                          " date text, time text, reported integer NULL DEFAULT 0)" 

  CREATE_TEMPERATURE_TABLE = "create table if not exists temperature " \
                        "(sensor_id name, temperature real, alarm integer, "\
                        "date text, time text, reported integer NULL DEFAULT 0)"

  CREATE_HEATING_TABLE = "create table if not exists heating " \
                        "(model_id name, sensor_id name, initial_temperature real, "\
                        " final_temperature real, delta_time real, zero_emission_ratio real, "\
                        "date text, time text, reported integer NULL DEFAULT 0)"

  INSERT_USER_TEMPLATE = "insert into user(" \
            "partition, pid, process, cpu_percent, cpu_time, " \
             "cpu_num_threads, memory_percent," \
             "memory_rss, io_rw_counter, io_cycles_counter, " \
             "date, time) values " \
             "('%s', %s, '%s', %s, %s, %s, %s, %s, %s, %s, '%s', '%s' )" 

  INSERT_FOLDER_TEMPLATE = "insert into folder(" \
            "partition, disk_used, date, time) values " \
             "('%s', %s, '%s', '%s' )" 

  INSERT_COMPUTER_TEMPLATE = "insert into computer("\
            " cpu_num_core, cpu_frequency, cpu_type," \
            "memory_size, memory_type, partition_list," \
            "date, time) values "\
            "(%s, %s, '%s', %s, '%s', '%s', '%s', '%s' )"

  INSERT_DISK_TEMPLATE = "insert into disk("\
            " partition, used, free, mountpoint," \
            " date, time) "\
            "values ('%s', %s,  %s, '%s', '%s', '%s' )"
    
  INSERT_SYSTEM_TEMPLATE = "insert into system("\
            " loadavg, cpu_percent, memory_used, memory_free," \
            " net_in_bytes, net_in_errors, net_in_dropped," \
            " net_out_bytes, net_out_errors, net_out_dropped, " \
            " date, time) values "\
            "( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '%s', '%s' )"

  INSERT_TEMPERATURE_TEMPLATE = "insert into temperature("\
            " sensor_id, temperature, alarm," \
            " date, time) values "\
            "( '%s', %s, %s, '%s', '%s' )"

  INSERT_HEATING_TEMPLATE = "insert into heating("\
            " model_id, sensor_id, initial_temperature, final_temperature, "\
            " delta_time, zero_emission_ratio," \
            " date, time) values "\
            "( '%s', '%s', %s, %s, %s, %s, '%s', '%s' )"

  def __init__(self, directory = None, create = True, timeout=None):
    assert self.database_name is not None
    self.uri = os.path.join(directory, self.database_name)
    self.connection = None
    self.cursor = None
    self.timeout = timeout
    if create:
      self._bootstrap()

  def connect(self):
    self.connection = sqlite_connect(self.uri, timeout=self.timeout)
    self.cursor = self.connection.cursor()

  def commit(self):
    assert self.connection is not None
    self.connection.commit()

  def close(self):
    assert self.connection is not None
    self.cursor.close()
    self.connection.close()

  def _execute(self, sql):
    assert self.connection is not None
    return self.cursor.execute(sql)

  def _bootstrap(self):
    assert self.CREATE_USER_TABLE is not None
    self.connect()
    self._execute(self.CREATE_USER_TABLE)
    self._execute(self.CREATE_USER_PARTITION_DATE_TIME_INDEX)
    self._execute(self.CREATE_FOLDER_TABLE)
    self._execute(self.CREATE_COMPUTER_TABLE)
    self._execute(self.CREATE_SYSTEM_TABLE)
    self._execute(self.CREATE_DISK_PARTITION)
    self._execute(self.CREATE_TEMPERATURE_TABLE)
    self._execute(self.CREATE_HEATING_TABLE)
    self.commit()
    self.close()

  def _getInsertionDateTuple(self):
    return strftime("%Y-%m-d -- %H:%M:%S").split(" -- ")

  ###################
  # Insertion methods
  ###################
  def insertUserSnapshot(self, partition, pid, process, cpu_percent, cpu_time, 
        cpu_num_threads, memory_percent, memory_rss, io_rw_counter, 
        io_cycles_counter, insertion_date, insertion_time):
    """ Insert user processes snapshots information on a database """
    insertion_sql = self.INSERT_USER_TEMPLATE % \
              ( partition, pid, process, cpu_percent, cpu_time,
                cpu_num_threads, memory_percent,
                memory_rss, io_rw_counter, io_cycles_counter,
                insertion_date, insertion_time)
    self._execute(insertion_sql)
    return insertion_sql

  def inserFolderSnapshot(self, partition, disk_usage, insertion_date, insertion_time):
    """ Insert folder disk usage snapshots information on a database """
    insertion_sql = self.INSERT_FOLDER_TEMPLATE % \
              ( partition, disk_usage, insertion_date, insertion_time)
    self._execute(insertion_sql)
    return insertion_sql

  def insertComputerSnapshot(self, cpu_num_core, cpu_frequency, cpu_type,
         memory_size, memory_type, partition_list, insertion_date, insertion_time):
    """Insert Computer general informations snapshots informations on 
       the database
    """
    insertion_sql = self.INSERT_COMPUTER_TEMPLATE % \
              ( cpu_num_core, cpu_frequency, cpu_type, 
                memory_size, memory_type, 
                partition_list, insertion_date, 
                insertion_time)
    self._execute(insertion_sql)  
    return insertion_sql

  def insertDiskPartitionSnapshot(self, partition, used, free, mountpoint,
                                        insertion_date, insertion_time):
    """ Insert Disk Partitions informations on the database """
    insertion_sql = self.INSERT_DISK_TEMPLATE % \
             ( partition, used, free, mountpoint, 
               insertion_date, insertion_time )
    self._execute(insertion_sql)  
    return insertion_sql
    
  def insertSystemSnapshot(self, loadavg, cpu_percent, memory_used, memory_free,
       net_in_bytes, net_in_errors, net_in_dropped, net_out_bytes, 
       net_out_errors, net_out_dropped, insertion_date, insertion_time):
    """ Include System general Snapshot on the database 
    """
    insertion_sql = self.INSERT_SYSTEM_TEMPLATE % \
             ( loadavg, cpu_percent, memory_used, memory_free,
               net_in_bytes, net_in_errors, net_in_dropped,
               net_out_bytes, net_out_errors, net_out_dropped,
               insertion_date, insertion_time )
    self._execute(insertion_sql)  
    return insertion_sql

  def insertTemperatureSnapshot(self, sensor_id, temperature, alarm,
        insertion_date, insertion_time):
    """ Include Temperature information Snapshot on the database 
    """
    insertion_sql = self.INSERT_TEMPERATURE_TEMPLATE % \
       (sensor_id, temperature, alarm, insertion_date, insertion_time)

    self._execute(insertion_sql)  
    return insertion_sql

  def insertHeatingSnapshot(self, model_id, sensor_id, initial_temperature, 
        final_temperature, delta_time, zero_emission_ratio,
        insertion_date, insertion_time):
    """ Include Heating information Snapshot on the database 
    """
    insertion_sql = self.INSERT_HEATING_TEMPLATE % \
       (model_id, sensor_id, initial_temperature, final_temperature, 
        delta_time, zero_emission_ratio, insertion_date, insertion_time)

    self._execute(insertion_sql)  
    return insertion_sql

  def getTableList(self):
    """ Get the list of tables from the database 
    """
    return [i[0] for i in self._execute(
           "SELECT name FROM sqlite_master WHERE type='table'")]

  def _getGarbageCollectionDateList(self, days_to_preserve=3):
    """ Return the list of dates to Preserve when data collect
    """
    base = datetime.datetime.today()
    date_list = []
    for x in range(0, days_to_preserve):
      date_list.append((base - datetime.timedelta(days=x)).strftime("%Y-%m-%d"))
    return date_list

  def garbageCollect(self):
    """ Garbase collect the database, by removing older records already
        reported.
    """
    date_list = self._getGarbageCollectionDateList()
    where_clause = "reported = 1" 
    for _date in date_list:
      where_clause += " AND date != '%s' " % _date
    
    delete_sql = "DELETE FROM %s WHERE %s"

    self.connect()
    for table in self.table_list:
      if table not in self.preserve_table_list: 
        self._execute(delete_sql % (table, where_clause))

    self.commit()
    self.close()

  def getDateScopeList(self, ignore_date=None, reported=0):
    """ Get from the present unique dates from the system
        Use a smaller table to sabe time.
    """
    if ignore_date is not None:
      where_clause = " AND date != '%s'" % ignore_date
    else:
      where_clause = ""
    select_sql = "SELECT date, count(time) FROM system "\
                 " WHERE reported = %s %s GROUP BY date" % \
                                    (reported, where_clause)
    return self._execute(select_sql)

  def markDayAsReported(self, date_scope, table_list):
    """ Mark all registers from a certain date as reported """
    update_sql = "UPDATE %s SET reported = 1 " \
                 "WHERE date = '%s' AND reported = 0"
    for table in table_list:
      self._execute(update_sql % (table, date_scope))

  def select(self, table, date=None, columns="*", where=None, order=None, group=None, limit=0):
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
    if group is not None:
      select_sql += " GROUP BY %s" % group
    if order is not None:
      select_sql += " ORDER BY %s" % order
    if limit:
      select_sql += " limit %s" % limit
    return self._execute(select_sql)


  #####################################################
  # Export Tables as Dict for handle realtime plotting
  #####################################################
  def exportSystemAsDict(self, date):
    """ Export system table as dictionally, formatting the output 
        for present it in a nicer presentation. 
    """  
    collected_entry_dict = {}

    collected_entry_dict["loadavg"] = []
    collected_entry_dict["cpu_percent"] = []
    collected_entry_dict["memory_used"] = []
    collected_entry_dict["memory_free"] = []
    collected_entry_dict["net_in_bytes"] = []
    collected_entry_dict["net_in_errors"] = []
    collected_entry_dict["net_in_dropped"] = []
    collected_entry_dict["net_out_bytes"] = []
    collected_entry_dict["net_out_errors"] = []
    collected_entry_dict["net_out_dropped"] = []

    first_entry = 1
    last_entry_in = 0
    last_entry_out = 0
    entry_list =  self._execute(
        "SELECT loadavg, cpu_percent, memory_used, memory_free," \
               " net_in_bytes, net_in_errors, net_in_dropped," \
               " net_out_bytes, net_out_errors, net_out_dropped, " \
               " date, time FROM system WHERE date = '%s'" % date) 

    for entry in entry_list:

      entry_time = "%s %s" % (entry[10], str(entry[11]))
      if not first_entry:
        _entry_in = entry[4] - last_entry_in
        last_entry_in = entry[4]
        entry_in = _entry_in

        _entry_out = entry[7] - last_entry_out
        last_entry_out = entry[7]
        entry_out = _entry_out
      
      else:
        first_entry = 0
        last_entry_in = entry[4]
        last_entry_out = entry[7]
        continue

      collected_entry_dict["loadavg"].append(
             {'entry': entry[0], 'time': entry_time })
      collected_entry_dict["cpu_percent"].append(
             {'entry': entry[1], 'time': entry_time })
      collected_entry_dict["memory_used"].append(
             {'entry': entry[2]/1024, 'time': entry_time })
      collected_entry_dict["memory_free"].append(
             {'entry': entry[3]/1024, 'time': entry_time })
      collected_entry_dict["net_in_bytes"].append(
             {'entry': entry_in/1024, 'time': entry_time })
      collected_entry_dict["net_in_errors"].append(
             {'entry': entry[5], 'time': entry_time })
      collected_entry_dict["net_in_dropped"].append(
             {'entry': entry[6], 'time': entry_time })
      collected_entry_dict["net_out_bytes"].append(
             {'entry': entry_out/1024, 'time': entry_time })
      collected_entry_dict["net_out_errors"].append(
             {'entry': entry[8], 'time': entry_time })
      collected_entry_dict["net_out_dropped"].append(
             {'entry': entry[9], 'time': entry_time })

    return collected_entry_dict

  def exportDiskAsDict(self, date):
    """ Export a column from a table for a given date.
    """
    collected_entry_dict = {}
    entry_list =  self._execute(
        "SELECT partition, used, free, date, time "\
        "from disk WHERE date = '%s'" % (date))

    for partition, used, free,  __date, __time in entry_list:
      partition_used = "%s-used" % partition
      partition_free = "%s-free" % partition
      if partition_used not in collected_entry_dict:
        collected_entry_dict[partition_used] = []

      if partition_free not in collected_entry_dict:
        collected_entry_dict[partition_free] = []

      collected_entry_dict[partition_used].append(
        {'entry': int(used)/1024, 
         'time': "%s %s" % (__date, str(__time))})

      collected_entry_dict[partition_free].append(
        {'entry': int(free)/1024, 
         'time': "%s %s" % (__date, str(__time))})

    return collected_entry_dict

  def getLastHeatingTestTime(self):
    select_sql = "SELECT date, time FROM heating ORDER BY date, time DESC LIMIT 1"
    for __date, __time in self._execute(select_sql):
       _date = datetime.datetime.strptime("%s %s" % (__date, __time), "%Y-%m-%d %H:%M:%S")
       return datetime.datetime.now() - _date
    return datetime.timedelta(weeks=520)

  def getLastZeroEmissionRatio(self):
    select_sql = "SELECT zero_emission_ratio FROM heating ORDER BY date, time DESC LIMIT 1"
    for entry in self._execute(select_sql):
       return entry[0]
    return -1 


  def getCollectedTemperatureList(self, sensor_id=None, limit=1):
    """ Query database for a full table information """
    if limit > 0:
      limit_clause = "LIMIT %s" % (limit,)
    else:
      limit_clause = ""

    if sensor_id is not None:
      where_clause = "WHERE sensor_id = '%s'" % (sensor_id)
    else:
      where_clause = ""

    select_sql = "SELECT * FROM temperature %s ORDER BY time DESC %s" % (where_clause, limit_clause)
    return self._execute(select_sql)

