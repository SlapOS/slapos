# coding: utf-8
import logging
import os
import os.path
import pwd
import time

from zope import interface as zope_interface
from slapos.manager import interface

logger = logging.getLogger(__name__)


class Manager(object):
  """Manage cgroup's cpuset in terms on initializing and runtime operations.

  CPUSET manager moves PIDs between CPU cores using Linux cgroup system.

  In order to use this feature put "cpuset" into "manager_list" into your slapos
  configuration file inside [slapos] section.

  TODO: there is no limit on number of reserved cores per user.
  """
  zope_interface.implements(interface.IManager)

  cpu_exclusive_file = ".slapos-cpu-exclusive"
  cpuset_path = "/sys/fs/cgroup/cpuset/"
  task_write_mode = "wt"
  config_power_user_option = "power_user_list"

  def __init__(self, config):
    """Retain access to dict-like configuration."""
    self.config = config

  def software(self, software):
    """We don't need to mingle with software."""
    pass

  def softwareTearDown(self, software):
    """We don't need to mingle with software."""
    pass

  def format(self, computer):
    """Create cgroup folder per-CPU with exclusive access to the CPU.

    - Those folders are "/sys/fs/cgroup/cpuset/cpu<N>".
    """
    if not os.path.exists(os.path.join(self.cpuset_path, "cpuset.cpus")):
      logger.warning("CPUSet Manager cannot format computer because cgroups do not exist.")
      return

    for cpu in self._cpu_id_list():
      cpu_path = self._prepare_folder(
        os.path.join(self.cpuset_path, "cpu" + str(cpu)))
      with open(cpu_path + "/cpuset.cpus", "wt") as fx:
        fx.write(str(cpu))  # this cgroup manages only this cpu
      with open(cpu_path + "/cpuset.cpu_exclusive", "wt") as fx:
        fx.write("1")  # manages it exclusively
      with open(cpu_path + "/cpuset.mems", "wt") as fx:
        fx.write("0")  # it doesn't work without that

  def formatTearDown(self, computer):
    pass

  def instance(self, partition):
    """Control runtime state of the computer."""

    if not os.path.exists(os.path.join(self.cpuset_path, "cpu0")):
      # check whether the computer was formatted
      logger.warning("CGROUP's CPUSET Manager cannot update computer because it is not cpuset-formatted.")
      return

    request_file = os.path.join(partition.instance_path, self.cpu_exclusive_file)
    if not os.path.exists(request_file) or not read_file(request_file):
      # This instance does not ask for cpu exclusive access
      return

    # Gather list of users allowed to request exlusive cores
    power_user_list = self.config.get(self.config_power_user_option, "").split()
    uid, gid = partition.getUserGroupId()
    uname = pwd.getpwuid(uid).pw_name
    if uname not in power_user_list:
      logger.warning("User {} not allowed to modify cpuset! "
                     "Allowed users are in {} option in config file.".format(
                        uname, self.config_power_user_option))
      return

    # prepare paths to tasks file for all and per-cpu
    tasks_file = os.path.join(self.cpuset_path, "tasks")
    cpu_tasks_file_list = [os.path.join(cpu_folder, "tasks")
                           for cpu_folder in self._cpu_folder_list()]

    # Gather exclusive CPU usage map {username: set[cpu_id]}
    # We do not need to gather that since we have no limits yet
    #cpu_usage = defaultdict(set)
    #for cpu_id in self._cpu_id_list()[1:]:  # skip the first public CPU
    #  pids = [int(pid)
    #          for pid in read_file(cpu_tasks_file_list[cpu_id]).splitlines()]
    #  for pid in pids:
    #    process = psutil.Process(pid)
    #    cpu_usage[process.username()].add(cpu_id)

    # Move all PIDs from the pool of all CPUs onto the first exclusive CPU.
    running_list = sorted(list(map(int, read_file(tasks_file).split())), reverse=True)
    first_cpu = self._cpu_id_list()[0]
    success_set, refused_set = set(), set()
    for pid in running_list:
      try:
        self._move_task(pid, first_cpu)
        success_set.add(pid)
        time.sleep(0.01)
      except IOError as e:
        refused_set.add(pid)
    logger.debug("Refused to move {:d} PIDs: {!s}\n"
                 "Suceeded in moving {:d} PIDs {!s}\n".format(
                     len(refused_set), refused_set, len(success_set), success_set))

    cpu_folder_list = self._cpu_folder_list()
    generic_cpu_path = cpu_folder_list[0]
    exclusive_cpu_path_list = cpu_folder_list[1:]

    # Gather all running PIDs for filtering out stale PIDs
    running_pid_set = set(running_list)
    running_pid_set.update(map(int, read_file(cpu_tasks_file_list[0]).split()))

    # gather already exclusively running PIDs
    exclusive_pid_set = set()
    for cpu_tasks_file in cpu_tasks_file_list[1:]:
      exclusive_pid_set.update(map(int, read_file(cpu_tasks_file).split()))

    # Move processes to their demanded exclusive CPUs
    with open(request_file, "rt") as fi:
      # take such PIDs which are either really running or are not already exclusive
      request_pid_list = [int(pid) for pid in fi.read().split()
                          if int(pid) in running_pid_set or int(pid) not in exclusive_pid_set]
    with open(request_file, "wt") as fo:
      fo.write("")  # empty file (we will write back only PIDs which weren't moved)
    for request_pid in request_pid_list:
      assigned_cpu = self._move_to_exclusive_cpu(request_pid)
      if assigned_cpu < 0:
        # if no exclusive CPU was assigned - write the PID back and try other time
        with open(request_file, "at") as fo:
          fo.write(str(request_pid) + "\n")

  def instanceTearDown(self):
    pass

  def _cpu_folder_list(self):
    """Return list of folders for exclusive cpu cores."""
    return [os.path.join(self.cpuset_path, "cpu" + str(cpu_id))
            for cpu_id in self._cpu_id_list()]

  def _cpu_id_list(self):
    """Extract IDs of available CPUs and return them as a list.

    The first one will be always used for all non-exclusive processes.
    :return: list[int]
    """
    cpu_list = []  # types: list[int]
    with open(self.cpuset_path + "cpuset.cpus", "rt") as cpu_def:
      for cpu_def_split in cpu_def.read().strip().split(","):
        # IDs can be in form "0-4" or "0,1,2,3,4"
        if "-" in cpu_def_split:
          a, b = map(int, cpu_def_split.split("-"))
          cpu_list.extend(range(a, b + 1)) # because cgroup's range is inclusive
          continue
        cpu_list.append(int(cpu_def_split))
    return cpu_list

  def _move_to_exclusive_cpu(self, pid):
    """Try all exclusive CPUs and place the ``pid`` to the first available one.

    :return: int, cpu_id of used CPU, -1 if placement was not possible
    """
    exclusive_cpu_list = self._cpu_id_list()[1:]
    for exclusive_cpu in exclusive_cpu_list:
      # gather tasks assigned to current exclusive CPU
      task_path = os.path.join(self.cpuset_path, "cpu" + str(exclusive_cpu), "tasks")
      with open(task_path, "rt") as fi:
        task_list = fi.read().split()
      if len(task_list) > 0:
        continue  # skip occupied CPUs
      return self._move_task(pid, exclusive_cpu)[1]
    return -1

  def _move_task(self, pid, cpu_id, cpu_mode="performance"):
    """Move ``pid`` to ``cpu_id``.

    cpu_mode can be "performance" or "powersave"
    """
    known_cpu_mode_list = ("performance", "powersave")
    with open(os.path.join(self.cpuset_path, "cpu" + str(cpu_id), "tasks"), self.task_write_mode) as fo:
      fo.write(str(pid) + "\n")
    # set the core to `cpu_mode`
    scaling_governor_file = "/sys/devices/system/cpu/cpu{:d}/cpufreq/scaling_governor".format(cpu_id)
    if os.path.exists(scaling_governor_file):
      if cpu_mode not in known_cpu_mode_list:
        logger.warning("Cannot set CPU to mode \"{}\"! Known modes {!s}".format(
          cpu_mode, known_cpu_mode_list))
      else:
        try:
          with open(scaling_governor_file, self.task_write_mode) as fo:
            fo.write(cpu_mode + "\n")  # default is "powersave"
        except IOError as e:
          # handle permission error
          logger.error("Failed to write \"{}\" to {}".format(cpu_mode, scaling_governor_file))
    return pid, cpu_id

  def _prepare_folder(self, folder):
    """If-Create folder and set group write permission."""
    if not os.path.exists(folder):
      os.mkdir(folder)
      # make your life and testing easier and create mandatory files if they don't exist
      mandatory_file_list = ("tasks", "cpuset.cpus")
      for mandatory_file in mandatory_file_list:
        file_path = os.path.join(folder, mandatory_file)
        if not os.path.exists(file_path):
          with open(file_path, "wb"):
            pass  # touche
    return folder


def read_file(path, mode="rt"):
  with open(path, mode) as fi:
    return fi.read()


def write_file(content, path, mode="wt"):
  with open(path, mode) as fo:
    fo.write(content)