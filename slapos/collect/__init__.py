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


from psutil import process_iter, NoSuchProcess, AccessDenied
from time import strftime
from slapos.collect.db import Database
from slapos.util import mkdir_p


from slapos.collect.snapshot import ProcessSnapshot, ComputerSnapshot
from slapos.collect.reporter import RawCSVDumper, \
                                    SystemCSVReporterDumper

from entity import get_user_list, Computer

def _get_time():
  return strftime("%Y-%m-%d -- %H:%M:%S").split(" -- ")

def build_snapshot(proc):
  try:
    return ProcessSnapshot(proc)
  except NoSuchProcess:
    return None

def current_state(user_dict):
  """
  Iterator used to apply build_snapshot(...) on every single relevant process.
  A process is considered relevant if its user matches our user list, i.e.
  its user is a slapos user
  """
  process_list = [p for p in process_iter() if p.username() in user_dict]
  for i, process in enumerate(process_list):
    yield build_snapshot(process)

def do_collect(conf):
  """
  Main function
  The idea here is to poll system every so many seconds
  For each poll, we get a list of Snapshots, holding informations about
  processes. We iterate over that list to store datas on a per user basis:
    Each user object is a dict, indexed on timestamp. We add every snapshot
    matching the user so that we get informations for each users
  """
  try:
    collected_date, collected_time = _get_time()
    user_dict = get_user_list(conf)
    try:
      for snapshot in current_state(user_dict):
        if snapshot:
          user_dict[snapshot.username].append(snapshot)
    except (KeyboardInterrupt, SystemExit, NoSuchProcess):
      raise
      
    log_directory = "%s/var/data-log" % conf.get("slapos", "instance_root")
    mkdir_p(log_directory, 0o755)
    database = Database(log_directory)

    computer = Computer(ComputerSnapshot())
    computer.save(database, collected_date, collected_time)

    for user in user_dict.values():
      user.save(database, collected_date, collected_time)
    
    SystemCSVReporterDumper(database).dump(log_directory)
    RawCSVDumper(database).dump(log_directory)

    # Drop older entries already reported
    database.garbageCollect()

  except AccessDenied:
    print "You HAVE TO execute this script with root permission."

