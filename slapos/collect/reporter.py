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

from lxml import etree as ElementTree
from slapos.util import mkdir_p

import csv
import glob
import json
import os
import os.path
import shutil
import tarfile
import time
import psutil

log_file = False

class Dumper(object):

  def __init__(self, database):
    self.db = database

  def dump(self, folder):
    raise NotImplemented("Implemented on Subclass")

  def writeFile(self, **kw):
    raise NotImplemented("Implemented on Subclass")

class SystemReporter(Dumper):
  
  def dump(self, folder):
    """ Dump data """
    _date = time.strftime("%Y-%m-%d")
    self.db.connect()
    for item, collected_item_list in self.db.exportSystemAsDict(_date).iteritems():
      self.writeFile(item, folder, collected_item_list)

    for partition, collected_item_list in self.db.exportDiskAsDict(_date).iteritems():
      partition_id = "_".join(partition.split("-")[:-1]).replace("/", "_")
      item = "memory_%s" % partition.split("-")[-1]
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
    date = time.strftime("%Y-%m-%d")
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
    mkdir_p(os.path.join(folder, date_scope), 0o755)
    file_io = open(os.path.join(folder, "%s/dump_%s.csv" % (date_scope, name)), "w")
    csv_output = csv.writer(file_io)
    csv_output.writerows(rows)
    file_io.close()

def compressLogFolder(log_directory):
  
    initial_folder = os.getcwd()
    os.chdir(log_directory)
    try:
      for backup_to_archive in glob.glob("*-*-*/"):
        filename = '%s.tar.gz' % backup_to_archive.strip("/")
        with tarfile.open(filename, 'w:gz') as tfile:
          tfile.add(backup_to_archive)
          tfile.close() 
        shutil.rmtree(backup_to_archive)
    finally:
      os.chdir(initial_folder)


class ConsumptionReportBase(object):
  def __init__(self, db):
    self.db = db

  def getPartitionCPULoadAverage(self, partition_id, date_scope):
    self.db.connect()
    query_result_cursor = self.db.select("user", date_scope,
                       columns="SUM(cpu_percent)", 
                       where="partition = '%s'" % partition_id)

    cpu_percent_sum = zip(*query_result_cursor)
    if len(cpu_percent_sum) and cpu_percent_sum[0][0] is None:
      return

    query_result_cursor = self.db.select("user", date_scope,
                       columns="COUNT(DISTINCT time)", 
                       where="partition = '%s'" % partition_id)

    sample_amount = zip(*query_result_cursor)
    self.db.close()

    if len(sample_amount) and len(cpu_percent_sum):
      return cpu_percent_sum[0][0]/sample_amount[0][0]

  def getPartitionUsedMemoryAverage(self, partition_id, date_scope):
    self.db.connect()
    query_result_cursor = self.db.select("user", date_scope,
                       columns="SUM(memory_rss)", 
                       where="partition = '%s'" % partition_id)

    memory_sum = zip(*query_result_cursor)
    if len(memory_sum) and memory_sum[0][0] is None:
      return

    query_result_cursor = self.db.select("user", date_scope,
                       columns="COUNT(DISTINCT time)", 
                       where="partition = '%s'" % partition_id)

    sample_amount = zip(*query_result_cursor)
    self.db.close()

    if len(sample_amount) and len(memory_sum):
      return memory_sum[0][0]/sample_amount[0][0]

  def getPartitionDiskUsedAverage(self, partition_id, date_scope):
    self.db.connect()
    query_result_cursor = self.db.select("folder", date_scope,
                       columns="SUM(disk_used)", 
                       where="partition = '%s'" % partition_id)

    disk_used_sum = zip(*query_result_cursor)
    if len(disk_used_sum) and disk_used_sum[0][0] is None:
      return
    query_result_cursor = self.db.select("folder", date_scope,
                       columns="COUNT(DISTINCT time)", 
                       where="partition = '%s'" % partition_id)

    collect_amount = zip(*query_result_cursor)
    self.db.close()

    if len(collect_amount) and len(disk_used_sum):
      return disk_used_sum[0][0]/collect_amount[0][0]

class ConsumptionReport(ConsumptionReportBase):

  def __init__(self, database, computer_id, location, user_list):
    self.computer_id = computer_id
    self.db = database
    self.user_list = user_list
    self.location = location
    ConsumptionReportBase.__init__(self, self.db)

  def buildXMLReport(self, date_scope):

     xml_report_path = "%s/%s.xml" % (self.location, date_scope)
     if os.path.exists(xml_report_path):
       return 

     if os.path.exists('%s.uploaded' % xml_report_path):
       return 

     journal = Journal()

     transaction = journal.newTransaction()

     journal.setProperty(transaction, "title", "Eco Information for %s " % self.computer_id)
     journal.setProperty(transaction, "start_date", "%s 00:00:00" % date_scope)
     journal.setProperty(transaction, "stop_date", "%s 23:59:59" % date_scope)
   
     journal.setProperty(transaction, "reference", "%s-global" % date_scope)

     journal.setProperty(transaction, "currency", "")
     journal.setProperty(transaction, "payment_mode", "")
     journal.setProperty(transaction, "category", "")

     arrow = ElementTree.SubElement(transaction, "arrow")
     arrow.set("type", "Destination")

     cpu_load_percent = self._getCpuLoadAverageConsumption(date_scope)

     if cpu_load_percent is not None:
       journal.newMovement(transaction, 
                           resource="service_module/cpu_load_percent",
                           title="CPU Load Percent Average",
                           quantity=str(cpu_load_percent), 
                           reference=self.computer_id,
                           category="")

     memory_used = self._getMemoryAverageConsumption(date_scope)

     if memory_used is not None:
       journal.newMovement(transaction, 
                           resource="service_module/memory_used",
                           title="Used Memory",
                           quantity=str(memory_used), 
                           reference=self.computer_id,
                           category="")


     if self._getZeroEmissionContribution() is not None:
       journal.newMovement(transaction, 
                           resource="service_module/zero_emission_ratio",
                           title="Zero Emission Ratio",
                           quantity=str(self._getZeroEmissionContribution()), 
                           reference=self.computer_id, 
                           category="")

     for user in self.user_list:
       partition_cpu_load_percent = self.getPartitionCPULoadAverage(user, date_scope)
       if partition_cpu_load_percent is not None:
         journal.newMovement(transaction,
                             resource="service_module/cpu_load_percent",
                             title="CPU Load Percent Average for %s" % (user),
                             quantity=str(partition_cpu_load_percent),
                             reference=user,
                             category="")

     mb = float(2 ** 20)
     for user in self.user_list:
       partition_memory_used = self.getPartitionUsedMemoryAverage(user, date_scope)
       if partition_memory_used is not None:
         journal.newMovement(transaction,
                             resource="service_module/memory_used",
                             title="Memory Used Average for %s" % (user),
                             quantity=str(partition_memory_used/mb),
                             reference=user,
                             category="")

     for user in self.user_list:
       partition_disk_used = self.getPartitionDiskUsedAverage(user, date_scope)
       if partition_disk_used is not None:
         journal.newMovement(transaction,
                           resource="service_module/disk_used",
                           title="Partition Disk Used Average for %s" % (user),
                           quantity=str(partition_disk_used/1024.0),
                           reference=user,
                           category="")

     with open(xml_report_path, 'w') as f:
       f.write(journal.getXML())
       f.close()

     return xml_report_path

  def _getAverageFromList(self, data_list):
    return sum(data_list)/len(data_list)

  def _getCpuLoadAverageConsumption(self, date_scope):
    self.db.connect()
    query_result_cursor = self.db.select("system", date_scope, 
                       columns="SUM(cpu_percent)/COUNT(cpu_percent)")

    cpu_load_percent_list = zip(*query_result_cursor)
    self.db.close()
    if len(cpu_load_percent_list):
      return cpu_load_percent_list[0][0]

  def _getMemoryAverageConsumption(self, date_scope):
    self.db.connect()
    query_result_cursor = self.db.select("system", date_scope, 
                       columns="SUM(memory_used)/COUNT(memory_used)")

    memory_used_list = zip(*query_result_cursor)
    self.db.close()
    if len(memory_used_list):
      return memory_used_list[0][0]

  def _getZeroEmissionContribution(self):
    self.db.connect()
    zer = self.db.getLastZeroEmissionRatio()  
    self.db.close()
    return zer

class Journal(object):

   def __init__(self):
     self.root = ElementTree.Element("journal")

   def getXML(self):
     report = ElementTree.tostring(self.root) 
     return "<?xml version='1.0' encoding='utf-8'?>%s" % report
   
   def newTransaction(self, portal_type="Sale Packing List"):
     transaction = ElementTree.SubElement(self.root, "transaction")
     transaction.set("type", portal_type)
     return transaction
   
   def setProperty(self, element, name, value):
   
     property_element = ElementTree.SubElement(element, name)
     property_element.text = value
   
   def newMovement(self, transaction, resource, title, 
                          quantity, reference, category):
   
     movement = ElementTree.SubElement(transaction, "movement")
 
     self.setProperty(movement, "resource", resource)
     self.setProperty(movement, "title", title)
     self.setProperty(movement, "reference", reference)
     self.setProperty(movement, "quantity", quantity)
     self.setProperty(movement, "price", "0.0")
     self.setProperty(movement, "VAT", "")
     # Provide units
     self.setProperty(movement, "category", category)
   
     return movement
 
