##############################################################################
#
# Copyright (c) 2014 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import glob
import unittest
import shutil
import tempfile
import slapos.slap
import psutil
from time import strftime
from slapos.cli.collect import CollectCommand
from slapos.collect import entity, snapshot, db, reporter
from slapos.cli.entry import SlapOSApp
from argparse import Namespace
from ConfigParser import ConfigParser

class FakeDatabase(object):
    def __init__(self):
      self.invoked_method_list = []

    def connect(self):
      self.invoked_method_list.append(("connect", ""))

    def close(self):
      self.invoked_method_list.append(("close", ""))

    def commit(self):
      self.invoked_method_list.append(("commit", ""))

    def insertUserSnapshot(self, *args, **kw):
      self.invoked_method_list.append(("insertUserSnapshot", (args, kw)))

    def insertSystemSnapshot(self, *args, **kw):
      self.invoked_method_list.append(("insertSystemSnapshot", (args, kw)))

    def insertComputerSnapshot(self, *args, **kw):
      self.invoked_method_list.append(("insertComputerSnapshot", (args, kw)))

    def insertDiskPartitionSnapshot(self, *args, **kw):
      self.invoked_method_list.append(("insertDiskPartitionSnapshot", (args, kw)))

class TestCollectDatabase(unittest.TestCase):

    def setUp(self):
        self.instance_root = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.instance_root):
          shutil.rmtree(self.instance_root)

    def test_database_bootstrap(self):
        self.assertFalse(os.path.exists(
                  "%s/collector.db" % self.instance_root ))
        database = db.Database(self.instance_root)
        database.connect()
        try:
          self.assertEquals(
              [u'user', u'computer', u'system', u'disk'],
              database.getTableList())
        finally:
          database.close()

        self.assertTrue(os.path.exists(
                  "%s/collector.db" % self.instance_root ))

    def test_insert_user_snapshot(self):

        database = db.Database(self.instance_root)
        database.connect()
        try:
            database.insertUserSnapshot(
             'fakeuser0', 10, '10-12345', '0.1', '10.0', '1',
             '10.0', '10.0', '0.1', '0.1', 'DATE', 'TIME')
            database.commit()
            self.assertEquals([i for i in database.select('user')], 
                            [(u'fakeuser0', 10.0, u'10-12345', 0.1, 10.0, 
                             1.0, 10.0, 10.0, 0.1, 0.1, u'DATE', u'TIME', 0)])
        finally:
            database.close()

    def test_insert_computer_snapshot(self):

        database = db.Database(self.instance_root)
        database.connect()
        try:
            database.insertComputerSnapshot(
              '1', '0', '0', '100', '0', '/dev/sdx1', 'DATE', 'TIME')
            database.commit()
            self.assertEquals([i for i in database.select('computer')], 
                    [(1.0, 0.0, u'0', 100.0, u'0', u'/dev/sdx1', u'DATE', u'TIME', 0)]) 
        finally:
          database.close()

    def test_insert_disk_partition_snapshot(self):

        database = db.Database(self.instance_root)
        database.connect()
        try:
            database.insertDiskPartitionSnapshot(
                 '/dev/sdx1', '10', '20', '/mnt', 'DATE', 'TIME')
            database.commit() 
            self.assertEquals([i for i in database.select('disk')], 
                            [(u'/dev/sdx1', u'10', u'20', u'/mnt', u'DATE', u'TIME', 0)])
        finally:
          database.close()

    def test_insert_system_snapshot(self):

        database = db.Database(self.instance_root)
        database.connect()
        try:
            database.insertSystemSnapshot("0.1", '10.0', '100.0', '100.0', 
                         '10.0', '1', '2', '12.0', '1', '1', 'DATE', 'TIME')
            database.commit()

            self.assertEquals([i for i in database.select('system')], 
                             [(0.1, 10.0, 100.0, 100.0, 10.0, 1.0, 
                               2.0, 12.0, 1.0, 1.0, u'DATE', u'TIME', 0)])
        finally:
          database.close()

    def test_date_scope(self):

        database = db.Database(self.instance_root)
        database.connect()
        try:
            database.insertSystemSnapshot("0.1", '10.0', '100.0', '100.0', 
                 '10.0', '1', '2', '12.0', '1', '1', 'EXPECTED-DATE', 'TIME')
            database.commit()

            self.assertEquals([i for i in database.getDateScopeList()], 
                             [('EXPECTED-DATE', 1)])

            self.assertEquals([i for i in \
               database.getDateScopeList(ignore_date='EXPECTED-DATE')], 
               [])

            self.assertEquals([i for i in \
               database.getDateScopeList(reported=1)], 
               [])

        finally:
          database.close()


    def test_mark_day_as_reported(self):

        database = db.Database(self.instance_root)
        database.connect()
        try:
            database.insertSystemSnapshot("0.1", '10.0', '100.0', '100.0', 
                 '10.0', '1', '2', '12.0', '1', '1', 'EXPECTED-DATE', 'TIME')
            database.insertSystemSnapshot("0.1", '10.0', '100.0', '100.0', 
                 '10.0', '1', '2', '12.0', '1', '1', 'NOT-EXPECTED-DATE', 'TIME')
            database.commit()

            self.assertEquals([i for i in database.select('system')], 
                             [(0.1, 10.0, 100.0, 100.0, 10.0, 1.0, 
                               2.0, 12.0, 1.0, 1.0, u'EXPECTED-DATE', u'TIME', 0),
                             (0.1, 10.0, 100.0, 100.0, 10.0, 1.0, 
                               2.0, 12.0, 1.0, 1.0, u'NOT-EXPECTED-DATE', u'TIME', 0)])

            database.markDayAsReported(date_scope="EXPECTED-DATE", 
                                       table_list=["system"])
            database.commit()

            self.assertEquals([i for i in database.select('system')], 
                             [(0.1, 10.0, 100.0, 100.0, 10.0, 1.0, 
                               2.0, 12.0, 1.0, 1.0, u'EXPECTED-DATE', u'TIME', 1),
                             (0.1, 10.0, 100.0, 100.0, 10.0, 1.0, 
                               2.0, 12.0, 1.0, 1.0, u'NOT-EXPECTED-DATE', u'TIME', 0)])

        finally:
          database.close()

class TestCollectReport(unittest.TestCase):

    def setUp(self):
        self.instance_root = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.instance_root):
          shutil.rmtree(self.instance_root)

    def test_raw_csv_report(self):

        database = db.Database(self.instance_root)
        database.connect()
        database.insertSystemSnapshot("0.1", '10.0', '100.0', '100.0', 
                         '10.0', '1', '2', '12.0', '1', '1', '1983-01-10', 'TIME')
        database.insertDiskPartitionSnapshot(
                 '/dev/sdx1', '10', '20', '/mnt', '1983-01-10', 'TIME')
        database.insertComputerSnapshot(
              '1', '0', '0', '100', '0', '/dev/sdx1', '1983-01-10', 'TIME')
        database.commit()
        database.close()
        reporter.RawCSVDumper(database).dump(self.instance_root)
        self.assertTrue(os.path.exists("%s/1983-01-10" % self.instance_root))

        csv_path_list = ['%s/1983-01-10/dump_disk.csv' % self.instance_root,
                         '%s/1983-01-10/dump_computer.csv' % self.instance_root,
                         '%s/1983-01-10/dump_user.csv' % self.instance_root,
                         '%s/1983-01-10/dump_system.csv' % self.instance_root]

        self.assertEquals(set(glob.glob("%s/1983-01-10/*.csv" % self.instance_root)),
                          set(csv_path_list))

    def test_system_csv_report(self):
        database = db.Database(self.instance_root)
        database.connect()
        database.insertSystemSnapshot("0.1", '10.0', '100.0', '100.0', 
                         '10.0', '1', '2', '12.0', '1', '1', strftime("%Y-%m-%d"), 'TIME')
        database.insertDiskPartitionSnapshot(
                 '/dev/sdx1', '10', '20', '/mnt', strftime("%Y-%m-%d"), 'TIME')
        database.insertComputerSnapshot(
              '1', '0', '0', '100', '0', '/dev/sdx1', strftime("%Y-%m-%d"), 'TIME')
        database.commit()
        database.close()

        reporter.SystemCSVReporterDumper(database).dump(self.instance_root)
        csv_path_list = ['%s/system_memory_used.csv' % self.instance_root,
                         '%s/system_cpu_percent.csv' % self.instance_root,
                         '%s/system_net_out_bytes.csv' % self.instance_root,
                         '%s/system_net_in_bytes.csv' % self.instance_root,
                         '%s/system_disk_memory_free_sdx1.csv' % self.instance_root,
                         '%s/system_net_out_errors.csv' % self.instance_root,
                         '%s/system_disk_memory_used_sdx1.csv' % self.instance_root,
                         '%s/system_net_out_dropped.csv' % self.instance_root,
                         '%s/system_memory_free.csv' % self.instance_root,
                         '%s/system_net_in_errors.csv' % self.instance_root,
                         '%s/system_net_in_dropped.csv' % self.instance_root,
                         '%s/system_loadavg.csv' % self.instance_root]

        self.assertEquals(set(glob.glob("%s/*.csv" % self.instance_root)), set(csv_path_list)) 

class TestCollectSnapshot(unittest.TestCase):

    def setUp(self):
        self.slap = slapos.slap.slap()
        self.app = SlapOSApp()
        self.temp_dir = tempfile.mkdtemp()
        os.environ["HOME"] = self.temp_dir
        self.instance_root = tempfile.mkdtemp()
        self.software_root = tempfile.mkdtemp()
        if os.path.exists(self.temp_dir):
          shutil.rmtree(self.temp_dir)

    def test_process_snapshot(self):
        process = psutil.Process(os.getpid())
        process_snapshot = snapshot.ProcessSnapshot(process)

        self.assertNotEquals(process_snapshot.username, None)  
        self.assertEquals(int(process_snapshot.pid), os.getpid())
        self.assertEquals(int(process_snapshot.name.split("-")[0]),
                          os.getpid())

        self.assertNotEquals(process_snapshot.cpu_percent , None)
        self.assertNotEquals(process_snapshot.cpu_time , None)
        self.assertNotEquals(process_snapshot.cpu_num_threads, None)
        self.assertNotEquals(process_snapshot.memory_percent , None)
        self.assertNotEquals(process_snapshot.memory_rss, None)
        self.assertNotEquals(process_snapshot.io_rw_counter, None)
        self.assertNotEquals(process_snapshot.io_cycles_counter, None)

    def test_process_snapshot_broken_process(self):
        self.assertRaises(AssertionError, 
                 snapshot.ProcessSnapshot, None)

    def test_computer_snapshot(self):
        computer_snapshot = snapshot.ComputerSnapshot()
        self.assertNotEquals(computer_snapshot.cpu_num_core , None)
        self.assertNotEquals(computer_snapshot.cpu_frequency , None)
        self.assertNotEquals(computer_snapshot.cpu_type , None)
        self.assertNotEquals(computer_snapshot.memory_size , None)
        self.assertNotEquals(computer_snapshot.memory_type , None)
        
        self.assertEquals(type(computer_snapshot.system_snapshot),  
                               snapshot.SystemSnapshot)

        self.assertNotEquals(computer_snapshot.disk_snapshot_list, [])
        self.assertNotEquals(computer_snapshot.partition_list, []) 

        self.assertEquals(type(computer_snapshot.disk_snapshot_list[0]), 
                snapshot.DiskPartitionSnapshot)

    def test_system_snapshot(self):
        system_snapshot = snapshot.SystemSnapshot()       
        self.assertNotEquals(system_snapshot.memory_used , None)
        self.assertNotEquals(system_snapshot.memory_free , None)
        self.assertNotEquals(system_snapshot.memory_percent , None)
        self.assertNotEquals(system_snapshot.cpu_percent , None)
        self.assertNotEquals(system_snapshot.load , None)
        self.assertNotEquals(system_snapshot.net_in_bytes , None)
        self.assertNotEquals(system_snapshot.net_in_errors, None)
        self.assertNotEquals(system_snapshot.net_in_dropped , None)
        self.assertNotEquals(system_snapshot.net_out_bytes , None)
        self.assertNotEquals(system_snapshot.net_out_errors, None)
        self.assertNotEquals(system_snapshot.net_out_dropped , None)
 
class TestCollectEntity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        os.environ["HOME"] = self.temp_dir
        self.instance_root = tempfile.mkdtemp()
        self.software_root = tempfile.mkdtemp()
        if os.path.exists(self.temp_dir):
          shutil.rmtree(self.temp_dir)

    def tearDown(self):
        pass

    def getFakeUser(self):
       return entity.User("fakeuser0", 
                    "%s/fakeuser0" % self.instance_root ) 

    def test_get_user_list(self):
        config = ConfigParser()
        config.add_section('slapformat')
        config.set('slapformat', 'partition_amount', '3')
        config.set('slapformat', 'user_base_name', 'slapuser')
        config.set('slapformat', 'partition_base_name', 'slappart')
        config.add_section('slapos')
        config.set('slapos', 'instance_root', self.instance_root)
 
        user_dict = entity.get_user_list(config)
        username_list = ['slapuser0', 'slapuser1', 'slapuser2'] 
        self.assertEquals(username_list, user_dict.keys())
       
        for name in username_list:
          self.assertEquals(user_dict[name].name, name)
          self.assertEquals(user_dict[name].snapshot_list, [])
          expected_path = "%s/slappart%s" % (self.instance_root, name.strip("slapuser")) 
          self.assertEquals(user_dict[name].path, expected_path) 
       
    def test_user_add_snapshot(self):
        user = self.getFakeUser() 
        self.assertEquals(user.snapshot_list, [])
        user.append("SNAPSHOT")
        self.assertEquals(user.snapshot_list, ["SNAPSHOT"])

    def test_user_save(self):
        user = self.getFakeUser()
        process = psutil.Process(os.getpid())
        user.append(snapshot.ProcessSnapshot(process))
        database = FakeDatabase()
        user.save(database, "DATE", "TIME")
        self.assertEquals(database.invoked_method_list[0], ("connect", ""))

        self.assertEquals(database.invoked_method_list[1][0], "insertUserSnapshot")
        self.assertEquals(database.invoked_method_list[1][1][0], ("fakeuser0",))
        self.assertEquals(database.invoked_method_list[1][1][1].keys(), 
                   ['cpu_time', 'cpu_percent', 'process',
                    'memory_rss', 'pid', 'memory_percent',
                    'io_rw_counter', 'insertion_date', 'insertion_time',
                    'io_cycles_counter', 'cpu_num_threads'])
        self.assertEquals(database.invoked_method_list[2], ("commit", ""))
        self.assertEquals(database.invoked_method_list[3], ("close", ""))

    def test_computer_entity(self):
        computer = entity.Computer(snapshot.ComputerSnapshot())
        database = FakeDatabase()
        computer.save(database, "DATE", "TIME")

        self.assertEquals(database.invoked_method_list[0], ("connect", ""))

        self.assertEquals(database.invoked_method_list[1][0], "insertComputerSnapshot")
        self.assertEquals(database.invoked_method_list[1][1][0], ())
        self.assertEquals(database.invoked_method_list[1][1][1].keys(), 
                 ['insertion_time', 'insertion_date', 'cpu_num_core',
                  'partition_list', 'cpu_frequency', 'memory_size', 
                  'cpu_type', 'memory_type'])
 
        self.assertEquals(database.invoked_method_list[2][0], "insertSystemSnapshot")
        self.assertEquals(database.invoked_method_list[2][1][0], ())
        self.assertEquals(set(database.invoked_method_list[2][1][1].keys()), 
          set([ 'memory_used', 'cpu_percent', 'insertion_date', 'insertion_time',
                'loadavg', 'memory_free', 'net_in_bytes', 'net_in_dropped', 
                'net_in_errors', 'net_out_bytes', 'net_out_dropped', 
                'net_out_errors']))

        self.assertEquals(database.invoked_method_list[3][0], "insertDiskPartitionSnapshot")
        self.assertEquals(database.invoked_method_list[3][1][0], ())
        self.assertEquals(set(database.invoked_method_list[3][1][1].keys()), 
          set([ 'used', 'insertion_date', 'partition', 'free', 
                'mountpoint', 'insertion_time' ]))

        self.assertEquals(database.invoked_method_list[-2], ("commit", ""))
        self.assertEquals(database.invoked_method_list[-1], ("close", ""))

