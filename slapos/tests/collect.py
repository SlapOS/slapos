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
import unittest
import shutil
import tempfile
import slapos.collect
import slapos.cli.collect
import slapos.slap
import psutil
from slapos.cli.collect import CollectCommand
from slapos.collect import entity, snapshot
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

    def tearDown(self):
        pass

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

