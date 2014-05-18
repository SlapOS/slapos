from psutil import process_iter, NoSuchProcess, AccessDenied
from time import time, sleep, strftime
from slapos.collect.db import Database
from slapos.util import mkdir_p
# Local import
from snapshot import ProcessSnapshot, SystemSnapshot, ComputerSnapshot
from slapos.collect.reporter import SystemJSONReporterDumper, \
                                    RawCSVDumper, \
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
    mkdir_p(log_directory)
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

