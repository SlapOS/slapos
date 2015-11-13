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
from datetime import datetime, timedelta
from slapos.collect.snapshot import FolderSizeSnapshot

def get_user_list(config):
  nb_user = int(config.get("slapformat", "partition_amount"))
  name_prefix = config.get("slapformat", "user_base_name")
  path_prefix = config.get("slapformat", "partition_base_name")
  instance_root = config.get("slapos", "instance_root")
  # By default, enable disk snapshot,
  # and set time_cycle to 24hours after the first disk snapshot run
  disk_snapshot_params = {'enable': True, 'time_cycle': 86400}
  if config.has_section('collect'):
    collect_section = dict(config.items("collect"))
    disk_snapshot_params = dict(
      enable=eval(collect_section.get("report_disk_usage", "True")),
      pid_folder=collect_section.get("disk_snapshot_process_pid_foder", None),
      time_cycle=int(collect_section.get("disk_snapshot_time_cycle", 86400)),
      use_quota=eval(collect_section.get("disk_snapshot_use_quota", "True"))
    )
  user_dict = {name: User(name, path, disk_snapshot_params)
      for name, path in [
          (
            "%s%s" % (name_prefix, nb),
            "%s/%s%s" % (instance_root, path_prefix, nb)
          ) for nb in range(nb_user)
        ]
      }

  #user_dict['root'] = User("root", "/opt/slapgrid")
  return user_dict

class User(object):
  def __init__(self, name, path, disk_snapshot_params={}):
    self.name = str(name)
    self.path = str(path)
    self.disk_snapshot_params = disk_snapshot_params
    self.snapshot_list = []

  def append(self, value):
    self.snapshot_list.append(value)

  def _insertDiskSnapShot(self, database, collected_date, collected_time):
    if self.disk_snapshot_params['enable']:
      time_cycle = self.disk_snapshot_params.get('time_cycle', 0)
      database.connect()
      if time_cycle:
        order = 'date DESC, time DESC'
        limit = 1
        query = database.select(table="folder", columns="date, time",
                                    order=order, limit=limit,
                                    where="partition='%s'" % self.name)
        query_result = zip(*query)
        if len(query_result):
          date, time = (query_result[0][0], query_result[1][0])
          latest_date = datetime.strptime('%s %s' % (date, time),
                                           "%Y-%m-%d %H:%M:%S")
          if (datetime.now() - latest_date).seconds < time_cycle:
            # wait the time cycle
            return
      pid_file = self.disk_snapshot_params.get('pid_folder', None)
      if pid_file is not None:
        pid_file = os.path.join(pid_file, '%s_disk_size.pid' % self.name)
      disk_snapshot = FolderSizeSnapshot(self.path, pid_file)
      disk_snapshot.update_folder_size()
      # Skeep insert empty partition: size <= 1Mb
      if disk_snapshot.disk_usage <= 1024.0 and \
                      not self.disk_snapshot_params.get('testing', False):
        return
      database.inserFolderSnapshot(self.name,
                disk_usage=disk_snapshot.get("disk_usage"),
                insertion_date=collected_date,
                insertion_time=collected_time)
      database.commit()
      database.close()

  def save(self, database, collected_date, collected_time):
    """ Insert collected data on user collector """
    database.connect()
    snapshot_counter = len(self.snapshot_list)
    for snapshot_item in self.snapshot_list:
      snapshot_item.update_cpu_percent()
      database.insertUserSnapshot(self.name,
            pid=snapshot_item.get("pid"),
            process=snapshot_item.get("process"),
            cpu_percent=snapshot_item.get("cpu_percent"),
            cpu_time=snapshot_item.get("cpu_time"),
            cpu_num_threads=snapshot_item.get("cpu_num_threads"),
            memory_percent=snapshot_item.get("memory_percent"),
            memory_rss=snapshot_item.get("memory_rss"),
            io_rw_counter=snapshot_item.get("io_rw_counter"),
            io_cycles_counter=snapshot_item.get("io_cycles_counter"),
            insertion_date=collected_date, 
            insertion_time=collected_time)
    database.commit()
    database.close()
    # Inser disk snapshot in a new transaction, it can take long
    self._insertDiskSnapShot(database, collected_date, collected_time)
    

class Computer(dict):

  def __init__(self, computer_snapshot):
    self.computer_snapshot = computer_snapshot

  def save(self, database, collected_date, collected_time):
    database.connect()
    self._save_computer_snapshot(database, collected_date, collected_time)
    self._save_system_snapshot(database, collected_date, collected_time)
    self._save_disk_partition_snapshot(database, collected_date, collected_time)
    self._save_temperature_snapshot(database, collected_date, collected_time)
    self._save_heating_snapshot(database, collected_date, collected_time)
    database.commit()
    database.close()

  def _save_computer_snapshot(self, database, collected_date, collected_time):
    partition_list = ";".join(["%s=%s" % (x,y) for x,y in \
                                  self.computer_snapshot.get("partition_list")])
    database.insertComputerSnapshot(
            cpu_num_core=self.computer_snapshot.get("cpu_num_core"), 
            cpu_frequency=self.computer_snapshot.get("cpu_frequency"),
            cpu_type=self.computer_snapshot.get("cpu_type"),
            memory_size=self.computer_snapshot.get("memory_size"),
            memory_type=self.computer_snapshot.get("memory_type"), 
            partition_list=partition_list,
            insertion_date=collected_date, 
            insertion_time=collected_time)

  def _save_system_snapshot(self, database, collected_date, collected_time):
    snapshot = self.computer_snapshot.get("system_snapshot")
    database.insertSystemSnapshot(
      loadavg=snapshot.get("load"),
      cpu_percent=snapshot.get("cpu_percent"), 
      memory_used=snapshot.get("memory_used"), 
      memory_free=snapshot.get("memory_free"),
      net_in_bytes=snapshot.get("net_in_bytes"),
      net_in_errors=snapshot.get("net_in_errors"),
      net_in_dropped=snapshot.get("net_in_dropped"),
      net_out_bytes=snapshot.get("net_out_bytes"),
      net_out_errors= snapshot.get("net_out_errors"),
      net_out_dropped=snapshot.get("net_out_dropped"),
      insertion_date=collected_date, 
      insertion_time=collected_time)

  def _save_disk_partition_snapshot(self, database, collected_date, collected_time):
    for disk_partition in self.computer_snapshot.get("disk_snapshot_list"):
      database.insertDiskPartitionSnapshot(
         partition=disk_partition.partition,
         used=disk_partition.disk_size_used,
         free=disk_partition.disk_size_free,
         mountpoint=';'.join(disk_partition.mountpoint_list),
         insertion_date=collected_date, 
         insertion_time=collected_time)

  def _save_temperature_snapshot(self, database, collected_date, collected_time):
    for temperature_snapshot in self.computer_snapshot.get("temperature_snapshot_list"):
      database.insertTemperatureSnapshot(
         sensor_id=temperature_snapshot.sensor_id,
         temperature=temperature_snapshot.temperature,
         alarm=temperature_snapshot.alarm,
         insertion_date=collected_date, 
         insertion_time=collected_time)

  def _save_heating_snapshot(self, database, collected_date, collected_time):
    heating_snapshot = self.computer_snapshot.get("heating_contribution_snapshot")
    if heating_snapshot is not None and \
         heating_snapshot.initial_temperature is not None:
      database.insertHeatingSnapshot(
         initial_temperature=heating_snapshot.initial_temperature,
         final_temperature=heating_snapshot.final_temperature,
         delta_time=heating_snapshot.delta_time,
         model_id=heating_snapshot.model_id, 
         sensor_id=heating_snapshot.sensor_id,
         zero_emission_ratio=heating_snapshot.zero_emission_ratio,
         insertion_date=collected_date, 
         insertion_time=collected_time)
