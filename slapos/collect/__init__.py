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
import shutil
import datetime
from slapos.collect.db import Database
from slapos.util import mkdir_p
import os
import stat

from slapos.collect.snapshot import ProcessSnapshot, ComputerSnapshot
from slapos.collect.reporter import RawCSVDumper, \
                                    SystemCSVReporterDumper, \
                                    compressLogFolder, \
                                    ConsumptionReport 

from entity import get_user_list, Computer

def _get_time():
  return strftime("%Y-%m-%d -- %H:%M:%S").split(" -- ")

def build_snapshot(proc):
  try:
    return ProcessSnapshot(proc)
  except NoSuchProcess:
    return None

def _get_uptime():
  # Linux only
  if os.path.exists('/proc/uptime'):
    with open('/proc/uptime', 'r') as f:
      return datetime.timedelta(seconds=float(f.readline().split()[0]))

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
    
    consumption_report_directory = "%s/var/consumption-report" % \
                                        conf.get("slapos", "instance_root") 
    mkdir_p(consumption_report_directory, 0o755)

    xml_report_directory = "%s/var/xml_report/%s" % \
                    (conf.get("slapos", "instance_root"), 
                     conf.get("slapos", "computer_id"))
    mkdir_p(xml_report_directory, 0o755)

    if stat.S_IMODE(os.stat(log_directory).st_mode) != 0o755:
      os.chmod(log_directory, 0o755)    

    database = Database(log_directory)

    if conf.has_option("slapformat", "computer_model_id"):
      computer_model_id = conf.get("slapformat", 
                                  "computer_model_id")
 
    else:
      computer_model_id = "no_model"

    uptime = _get_uptime()
    if conf.has_option("slapformat", "heating_sensor_id"):
      heating_sensor_id = conf.get("slapformat", 
                                  "heating_sensor_id")
      database.connect()
      test_heating = uptime is not None and \
                     uptime > datetime.timedelta(seconds=86400) and \
                     database.getLastHeatingTestTime() > uptime
      database.close()

    else:
      heating_sensor_id = "no_sensor"
      test_heating = False

    computer = Computer(ComputerSnapshot(model_id=computer_model_id, 
                                     sensor_id = heating_sensor_id,
                                     test_heating=test_heating))

    computer.save(database, collected_date, collected_time)

    for user in user_dict.values():
      user.save(database, collected_date, collected_time)
    
    SystemCSVReporterDumper(database).dump(log_directory)
    RawCSVDumper(database).dump(log_directory)
    consumption_report = ConsumptionReport(
                      computer_id=conf.get("slapos", "computer_id"), 
                      user_list=get_user_list(conf), 
                      database=database,
                      location=consumption_report_directory)
    
    base = datetime.datetime.today()
    for x in range(1, 3):
      report_file = consumption_report.buildXMLReport(
          (base - datetime.timedelta(days=x)).strftime("%Y-%m-%d"))

      if report_file is not None:
        shutil.copy(report_file, xml_report_directory)

    compressLogFolder(log_directory)

    # Drop older entries already reported
    database.garbageCollect()

  except AccessDenied:
    print "You HAVE TO execute this script with root permission."

