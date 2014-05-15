#!/usr/bin/env python

from slapos.collect.db import Database
from slapos.util import mkdir_p
import os.path
import json
import csv
from time import strftime

class Dumper(object):

  def __init__(self, database):
    self.db = database

class SystemReporter(Dumper):
  
  def dump(self, folder):
    """ Dump data """
    _date = strftime("%Y-%m-%d")
    self.db.connect()
    for item, collected_item_list in self.db.exportSystemAsDict(_date).iteritems():
      self.writeFile(item, folder, collected_item_list)

    for partition, collected_item_list in self.db.exportDiskAsDict(_date).iteritems():
      partition_id = partition.split("-")[0].split("/")[-1]
      item = "memory_%s" % partition.split("-")[1]
      self.writeFile("disk_%s_%s" % (item, partition_id), folder, collected_item_list)

    self.db.close()

class SystemJSONReporterDumper(SystemReporter):

  def writeFile(self, name, folder, collected_entry_list=[]):
    """ Dump data as json """
    file_io = open(os.path.join(folder, "system_%s.json" % name), "w")
    json.dump(collected_entry_list, file_io, sort_keys=True, indent=2)
    file_io.close()

class SystemCSVReporterDumper(SystemReporter):

  def writeFile(self, name, folder, collected_entry_list=[]):
    """ Dump data as json """
    file_io = open(os.path.join(folder, "system_%s.csv" % name), "w")
    csv_output = csv.writer(file_io)
    csv_output.writerow(["time", "entry"])
    for collected_entry in collected_entry_list:
      csv_output.writerow([collected_entry["time"], collected_entry["entry"]])
    file_io.close()

class RawDumper(Dumper):
  """ Dump raw data in a certain format
  """
  def dump(self, folder):
    date = strftime("%Y-%m-%d")
    self.db.connect()
    table_list = self.db.getTableList()
    for date_scope, amount in self.db.getDateScopeList(ignore_date=date):
      for table in table_list:
        self.writeFile(table, folder, date_scope, 
              self.db.select(table, date_scope))

      self.db.markDayAsReported(date_scope, 
                                table_list=table_list)
    self.db.commit()
    self.db.close()

class RawCSVDumper(RawDumper):
  
  def writeFile(self, name, folder, date_scope, rows):
    mkdir_p(os.path.join(folder, date_scope))
    file_io = open(os.path.join(folder, "%s/dump_%s.csv" % (date_scope, name)), "w")
    csv_output = csv.writer(file_io)
    csv_output.writerows(rows)
    file_io.close()

