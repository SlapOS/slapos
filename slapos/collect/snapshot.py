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

import psutil
import os

class _Snapshot(object):
  def get(self, property, default=None):
    return getattr(self, property, default)

class ProcessSnapshot(_Snapshot):
  """ Take a snapshot from the running process
  """
  def __init__(self, process=None):
    assert type(process) is psutil.Process
    ui_counter_list = process.get_io_counters()
    self.username = process.username()
    self.pid = process.pid 
    # Save full command line from the process.
    self.name = "%s-%s" % (process.pid, process.create_time())
    # CPU percentage, we will have to get actual absolute value
    self.cpu_percent = process.get_cpu_percent(None)
    # CPU Time
    self.cpu_time = sum(process.get_cpu_times())
    # Thread number, might not be really relevant
    self.cpu_num_threads = process.get_num_threads()      
    # Memory percentage
    self.memory_percent = process.get_memory_percent()
    # Resident Set Size, virtual memory size is not accouned for
    self.memory_rss = process.get_memory_info()[0]
    # Byte count, Read and write. OSX NOT SUPPORTED
    self.io_rw_counter = ui_counter_list[2] + ui_counter_list[3]
    # Read + write IO cycles
    self.io_cycles_counter  = ui_counter_list[0] + ui_counter_list[1]

class SystemSnapshot(_Snapshot):
  """ Take a snapshot from current system usage
  """
  def __init__(self):
    memory = psutil.phymem_usage()
    net_io = psutil.net_io_counters()
    
    self.memory_used = memory.used
    self.memory_free = memory.free
    self.memory_percent = memory.percent
    self.cpu_percent = psutil.cpu_percent()
    self.load = os.getloadavg()[0]
    self.net_in_bytes = net_io.bytes_recv
    self.net_in_errors = net_io.errin
    self.net_in_dropped = net_io.dropin
    self.net_out_bytes = net_io.bytes_sent
    self.net_out_errors = net_io.errout
    self.net_out_dropped = net_io.dropout

class DiskPartitionSnapshot(_Snapshot):
  """ Take Snapshot from general disk partitions 
      usage 
  """
  def __init__(self, partition, mountpoint):
    self.partition = partition
    self.mountpoint_list = [ mountpoint ]
    disk = psutil.disk_usage(mountpoint)
    disk_io = psutil.disk_io_counters()

    self.disk_size_used = disk.used
    self.disk_size_free = disk.free
    self.disk_size_percent = disk.percent

class ComputerSnapshot(_Snapshot):
  """ Take a snapshot from computer informations
  """
  def __init__(self):
    self.cpu_num_core = psutil.NUM_CPUS
    self.cpu_frequency = 0
    self.cpu_type = 0
    self.memory_size = psutil.TOTAL_PHYMEM  
    self.memory_type = 0

    #
    # Include a SystemSnapshot and a list DiskPartitionSnapshot
    # on a Computer Snapshot
    #
    self.system_snapshot = SystemSnapshot()
    self.disk_snapshot_list = []
    self.partition_list = self._get_physical_disk_info()

  def _get_physical_disk_info(self):
    partition_dict = {}

    for partition in psutil.disk_partitions():
      if partition.device not in partition_dict:
        usage = psutil.disk_usage(partition.mountpoint)
        partition_dict[partition.device] = usage.total
        self.disk_snapshot_list.append(
          DiskPartitionSnapshot(partition.device, 
                                partition.mountpoint))

    return [(k, v) for k, v in partition_dict.iteritems()]

