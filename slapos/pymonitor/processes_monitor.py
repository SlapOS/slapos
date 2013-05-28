from psutil import *
from psutil._error import NoSuchProcess, AccessDenied

from time import time, sleep
from datetime import datetime
import os
import ConfigParser

# Local import
from snapshot import Snapshot
from user import User

# XXX : this is BAAAAD !!
# ***************** Config *****************
GLOBAL_SLAPOS_CONFIGURATION = os.environ.get(
  'SLAPOS_CONFIGURATION',
  '/etc/opt/slapos/slapos.cfg'
)
# ******************************************


# XXX : should rebuild this to make it more explicit
def build_user_list():
  config = ConfigParser.SafeConfigParser()
  config.read(GLOBAL_SLAPOS_CONFIGURATION)
  nb_user = int(config.get("slapformat", "partition_amount"))
  name_prefix = config.get("slapformat", "user_base_name")
  path_prefix = config.get("slapformat", "partition_base_name")
  instance_root = config.get("slapos", "instance_root")
  return {name: User(name, path)
      for name, path in [
          (
            "%s%s" % (name_prefix, nb),
            "%s/%s%s" % (instance_root, path_prefix, nb)
          ) for nb in range(nb_user)
        ]
      }


def build_snapshot(proc):
  assert type(proc) is Process
  try:
    return Snapshot(
        proc.username,
        # CPU percentage, we will have to get actual absolute value
        cpu    = proc.get_cpu_percent(None),
        # Thread number, might not be really relevant
        cpu_io = proc.get_num_threads(),
        # Resident Set Size, virtual memory size is not accounted for
        ram    = proc.get_memory_info()[0],
        # Byte count, Read and write. OSX NOT SUPPORTED
        hd     = proc.get_io_counters()[2] + proc.get_io_counters()[3],
        # Read + write IO cycles
        hd_io  = proc.get_io_counters()[0] + proc.get_io_counters()[1],
    )
  except NoSuchProcess:
    return None

def current_state():
  """
  Iterator used to apply build_snapshot(...) on every single relevant process.
  A process is considered relevant if its user matches our user list, i.e.
  its user is a slapos user
  """
  users = build_user_list()
  pList = [p for p in process_iter() if p.username in users]
  length = len(pList) / 5
  for i, process in enumerate(pList):
    if length > 0 and i % length == 0:
      sleep(.5)
    yield build_snapshot(process)

def main():
  """
  Main function
  The idea here is to poll system every so many seconds
  For each poll, we get a list of Snapshots, holding informations about
  processes. We iterate over that list to store datas on a per user basis:
    Each user object is a dict, indexed on timestamp. We add every snapshot
    matching the user so that we get informations for each users
  """
  try:
    while True:
      users = build_user_list()
      key = time()
      try:
        for snapshot in current_state():
          if snapshot:
            user = users[snapshot.username]
            if key in user:
              user[key] += snapshot
            else:
              user[key] = snapshot
      except NoSuchProcess:
        continue
      except (KeyboardInterrupt, SystemExit):
        break

      # XXX: we should use a value from the config file and not a hardcoded one
      for user in users.values():
        user.dumpSummary(user.path + '/var/xml_report/consumption.xml')

  except AccessDenied:
    print "You HAVE TO execute this script with root permission."

if __name__  == '__main__':
  main()
