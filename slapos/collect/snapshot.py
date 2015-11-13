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
import subprocess
from temperature import collectComputerTemperature, \
                        launchTemperatureTest

from temperature.heating import get_contribution_ratio

MEASURE_INTERVAL = 5

class _Snapshot(object):
  def get(self, property, default=None):
    return getattr(self, property, default)

class ProcessSnapshot(_Snapshot):
  """ Take a snapshot from the running process
  """
  def __init__(self, process=None):
    assert type(process) is psutil.Process
    ui_counter_list = process.io_counters()
    self.username = process.username()
    self.process_object = process
    self.pid = process.pid 
    # Save full command line from the process.
    self.process = "%s-%s" % (process.pid, process.create_time())
    # CPU percentage, we will have to get actual absolute value
    self.cpu_percent = self.process_object.cpu_percent(None)
    # CPU Time
    self.cpu_time = sum(process.cpu_times())
    # Thread number, might not be really relevant
    self.cpu_num_threads = process.num_threads()
    # Memory percentage
    self.memory_percent = process.memory_percent()
    # Resident Set Size, virtual memory size is not accouned for
    self.memory_rss = process.memory_info()[0]
    # Byte count, Read and write. OSX NOT SUPPORTED
    self.io_rw_counter = ui_counter_list[2] + ui_counter_list[3]
    # Read + write IO cycles
    self.io_cycles_counter  = ui_counter_list[0] + ui_counter_list[1]

  def update_cpu_percent(self):
    if self.process_object.is_running():
      # CPU percentage, we will have to get actual absolute value
      self.cpu_percent = self.process_object.cpu_percent()

class FolderSizeSnapshot(_Snapshot):
  """Calculate partition folder size. 
  """
  def __init__(self, folder_path, pid_file=None, use_quota=False):
    # slapos computer partition size
    self.folder_path = folder_path
    self.pid_file = pid_file
    self.disk_usage = 0
    self.use_quota = use_quota

  def update_folder_size(self):
    """Return 0 if the process du is still running
    """
    if self.pid_file and os.path.exists(self.pid_file):
      with open(self.pid_file, 'r') as fpid:
        pid_str = fpid.read()
        if pid_str:
          pid = int(pid_str)
          try:
            os.kill(pid, 0)
          except OSError:
            pass
          else:
            return

    self.disk_usage = self._getSize(self.folder_path)
    # If extra disk added to partition
    data_dir = os.path.join(self.folder_path, 'DATA')
    if os.path.exists(data_dir):
      for filename in os.listdir(data_dir):
        extra_path = os.path.join(data_dir, filename)
        if os.path.islink(extra_path) and os.path.isdir('%s/' % extra_path):
          self.disk_usage += self._getSize('%s/' % extra_path)

  def _getSize(self, file_path):
    size = 0
    command = 'du -s %s' % file_path
    process = subprocess.Popen(command, stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, shell=True)
    if self.pid_file:
      with open(self.pid_file, 'w') as fpid:
        pid = fpid.write(str(process.pid))
    result = process.communicate()[0]
    if process.returncode == 0:
      size, _  = result.strip().split()
    return float(size)

class SystemSnapshot(_Snapshot):
  """ Take a snapshot from current system usage
  """
  def __init__(self, interval=MEASURE_INTERVAL):

    cpu_idle_percentage = psutil.cpu_times_percent(interval=interval).idle
    load_percent = 100 - cpu_idle_percentage

    memory = psutil.virtual_memory()
    net_io = psutil.net_io_counters()
    
    self.memory_used = memory.used
    self.memory_free = memory.free
    self.memory_percent = memory.percent
    #self.cpu_percent = psutil.cpu_percent()
    self.cpu_percent = load_percent
    self.load = os.getloadavg()[0]
    self.net_in_bytes = net_io.bytes_recv
    self.net_in_errors = net_io.errin
    self.net_in_dropped = net_io.dropin
    self.net_out_bytes = net_io.bytes_sent
    self.net_out_errors = net_io.errout
    self.net_out_dropped = net_io.dropout

class TemperatureSnapshot(_Snapshot):
  """ Take a snapshot from the current temperature on 
      all available sensors
  """
  def __init__(self, sensor_id, temperature, alarm):
    self.sensor_id = sensor_id
    self.temperature = temperature
    self.alarm = alarm

class HeatingContributionSnapshot(_Snapshot):

  def __init__(self, sensor_id, model_id):
    self.initial_temperature = None
    
    result = launchTemperatureTest(sensor_id)
    if result is None:
      print "Impossible to test sensor: %s " % sensor_id
      

    initial_temperature, final_temperature, duration = result 
    
    self.initial_temperature = initial_temperature
    self.final_temperature = final_temperature
    self.delta_time = duration
    self.model_id = model_id
    self.sensor_id = sensor_id
    self.zero_emission_ratio = self._get_contribution_ratio()

  def _get_contribution_ratio(self):
    delta_temperature = (self.final_temperature-self.initial_temperature)
    contribution_value = delta_temperature/self.delta_time
    return get_contribution_ratio(self.model_id, contribution_value)

  def _get_uptime(self):
    # Linux only
    if os.path.exists('/proc/uptime'):
      with open('/proc/uptime', 'r') as f:
        return float(f.readline().split()[0])

    return -1


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
  def __init__(self, model_id=None, sensor_id=None, test_heating=False):
    self.cpu_num_core = psutil.cpu_count()
    self.cpu_frequency = 0
    self.cpu_type = 0
    self.memory_size = psutil.virtual_memory().total
    self.memory_type = 0

    #
    # Include a SystemSnapshot and a list DiskPartitionSnapshot
    # on a Computer Snapshot
    #
    self.system_snapshot = SystemSnapshot()
    self.temperature_snapshot_list = self._get_temperature_snapshot_list()
    self.disk_snapshot_list = []
    self.partition_list = self._get_physical_disk_info()

    if test_heating and model_id is not None \
                    and sensor_id is not None:
      self.heating_contribution_snapshot = HeatingContributionSnapshot(sensor_id, model_id)

  def _get_temperature_snapshot_list(self):
    temperature_snapshot_list = []
    for sensor_entry in collectComputerTemperature():
      sensor_id, temperature, maximal, critical, alarm = sensor_entry
      temperature_snapshot_list.append(
          TemperatureSnapshot(sensor_id, temperature, alarm))
    return temperature_snapshot_list

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

  
