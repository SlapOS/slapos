# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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

import grp
import hashlib
import os
import pkg_resources
import pwd
import stat
import subprocess
import sys
import logging
import psutil
import time

from slapos.grid.exception import BuildoutFailedError, WrongPermissionError

# Such umask by default will create paths with full permission
# for user, non writable by group and not accessible by others
SAFE_UMASK = 0o27

PYTHON_ENVIRONMENT_REMOVE_LIST = [
  'PYTHONHOME',
  'PYTHONPATH',
  'PYTHONSTARTUP',
  'PYTHONY2K',
  'PYTHONOPTIMIZE',
  'PYTHONDEBUG',
  'PYTHONDONTWRITEBYTECODE',
  'PYTHONINSPECT',
  'PYTHONNOUSERSITE',
  'PYTHONNOUSERSITE',
  'PYTHONUNBUFFERED',
  'PYTHONVERBOSE',
]

SYSTEM_ENVIRONMENT_REMOVE_LIST = [
  'CONFIG_SITE',
  'ENV',
  'LOGNAME',
  'TEMP',
  'TMP',
  'TMPDIR',
]

LOCALE_ENVIRONMENT_REMOVE_LIST = [
  'LANG',
  'LANGUAGE',
  'LC_ADDRESS',
  'LC_COLLATE',
  'LC_CTYPE',
  'LC_IDENTIFICATION',
  'LC_MEASUREMENT',
  'LC_MESSAGES',
  'LC_MONETARY',
  'LC_NAME',
  'LC_NUMERIC',
  'LC_PAPER',
  'LC_SOURCED',
  'LC_TELEPHONE',
  'LC_TIME',
]

class SlapPopen(subprocess.Popen):
  """
  Almost normal subprocess with greedish features and logging.
  Each line is logged "live", and self.output is a string containing the whole
  log.
  """
  def __init__(self, *args, **kwargs):
    logger = kwargs.pop('logger')
    kwargs.update(stdin=subprocess.PIPE)
    if sys.platform == 'cygwin' and kwargs.get('env') == {}:
      kwargs['env'] = None

    # don't leak log & co. filedescriptors to child process
    kwargs.setdefault('close_fds', True)

    subprocess.Popen.__init__(self, *args, **kwargs)
    self.stdin.flush()
    self.stdin.close()
    self.stdin = None

    # XXX-Cedric: this algorithm looks overkill for simple logging.
    output_lines = []
    while True:
      line = self.stdout.readline()
      if line == '' and self.poll() is not None:
        break
      if line:
        output_lines.append(line)
        logger.info(line.rstrip('\n'))
    self.output = ''.join(output_lines)


def md5digest(url):
  return hashlib.md5(url).hexdigest()


def getCleanEnvironment(logger, home_path='/tmp'):
  changed_env = {}
  removed_env = []
  env = os.environ.copy()
  # Clean python related environment variables
  for k in PYTHON_ENVIRONMENT_REMOVE_LIST + SYSTEM_ENVIRONMENT_REMOVE_LIST \
        + LOCALE_ENVIRONMENT_REMOVE_LIST:
    old = env.pop(k, None)
    if old is not None:
      removed_env.append(k)
  changed_env['HOME'] = env['HOME'] = home_path
  for k in sorted(changed_env.iterkeys()):
    logger.debug('Overridden %s = %r' % (k, changed_env[k]))
  if removed_env:
    logger.debug('Removed from environment: %s' % ', '.join(sorted(removed_env)))
  return env


def setRunning(logger, pidfile):
  """Creates a pidfile. If a pidfile already exists, we exit"""
  # XXX might use http://code.activestate.com/recipes/577911-context-manager-for-a-daemon-pid-file/
  if os.path.exists(pidfile):
    try:
      pid = int(open(pidfile, 'r').readline())
    except ValueError:
      pid = None
    # XXX This could use psutil library.
    if pid and os.path.exists("/proc/%s" % pid):
      logger.info('New slapos process started, but another slapos '
                  'process is aleady running with pid %s, exiting.' % pid)
      sys.exit(10)
    logger.info('Existing pid file %r was stale, overwritten' % pidfile)
  # Start new process
  write_pid(logger, pidfile)


def setFinished(pidfile):
  try:
    os.remove(pidfile)
  except OSError:
    pass


def write_pid(logger, pidfile):
  try:
    with open(pidfile, 'w') as fout:
      fout.write('%s' % os.getpid())
  except (IOError, OSError):
    logger.critical('slapgrid could not write pidfile %s' % pidfile)
    raise


def dropPrivileges(uid, gid, logger):
  """Drop privileges to uid, gid if current uid is 0

  Do tests to check if dropping was successful and that no system call is able
  to re-raise dropped privileges

  Does nothing if uid and gid are not 0
  """
  # XXX-Cedric: remove format / just do a print, otherwise formatting is done
  # twice
  current_uid, current_gid = os.getuid(), os.getgid()
  if uid == 0 or gid == 0:
    raise OSError('Dropping privileges to uid = %r or '
                  'gid = %r is too dangerous' % (uid, gid))
  if (current_uid or current_gid):
    logger.debug('Running as uid = %r, gid = %r, dropping '
                 'not needed and not possible' % (current_uid, current_gid))
    return
  # drop privileges
  user_name = pwd.getpwuid(uid)[0]
  group_list = set(x.gr_gid for x in grp.getgrall() if user_name in x.gr_mem)
  group_list.add(gid)
  os.initgroups(pwd.getpwuid(uid)[0], gid)
  os.setgid(gid)
  os.setuid(uid)

  # assert that privileges are dropped
  message_pre = 'After dropping to uid = %r and gid = %r ' \
                'and group_list = %s' % (uid, gid, group_list)
  new_uid, new_gid, new_group_list = os.getuid(), os.getgid(), os.getgroups()
  if not (new_uid == uid and new_gid == gid and set(new_group_list) == group_list):
    raise OSError('%s new_uid = %r and new_gid = %r and '
                  'new_group_list = %r which is fatal.'
                    % (message_pre,
                       new_uid,
                       new_gid,
                       new_group_list))

  # assert that it is not possible to go back to running one
  try:
    try:
      os.setuid(current_uid)
    except OSError:
      try:
        os.setgid(current_gid)
      except OSError:
        try:
          os.setgroups([current_gid])
        except OSError:
          raise
  except OSError:
    pass
  else:
    raise ValueError('%s it was possible to go back to uid = %r and gid = '
                     '%r which is fatal.' % (message_pre, current_uid, current_gid))
  logger.debug('Succesfully dropped privileges to uid=%r gid=%r' % (uid, gid))


def bootstrapBuildout(path, logger, buildout=None,
                      additional_buildout_parameter_list=None):
  if additional_buildout_parameter_list is None:
    additional_buildout_parameter_list = []
  # Reads uid/gid of path, launches buildout with thoses privileges
  stat_info = os.stat(path)
  uid = stat_info.st_uid
  gid = stat_info.st_gid

  invocation_list = [sys.executable, '-S']
  if buildout is not None:
    invocation_list.append(buildout)
    invocation_list.extend(additional_buildout_parameter_list)
  else:
    try:
      __import__('zc.buildout')
    except ImportError:
      logger.warning('Using old style bootstrap of included bootstrap file. '
        'Consider having zc.buildout available in search path.')
      invocation_list.append(pkg_resources.resource_filename(__name__,
        'zc.buildout-bootstrap.py'))
      invocation_list.extend(additional_buildout_parameter_list)
    else:
      # buildout is importable, so use this one
      invocation_list.extend(["-c", "import sys ; sys.path=" + str(sys.path) +
        " ; import zc.buildout.buildout ; sys.argv[1:1]=" +
        repr(additional_buildout_parameter_list + ['bootstrap']) + " ; "
        "zc.buildout.buildout.main()"])

  if buildout is not None:
    invocation_list.append('bootstrap')
  try:
    umask = os.umask(SAFE_UMASK)
    logger.debug('Set umask from %03o to %03o' % (umask, SAFE_UMASK))
    logger.debug('Invoking: %r in directory %r' % (' '.join(invocation_list),
      path))
    process_handler = SlapPopen(invocation_list,
                                preexec_fn=lambda: dropPrivileges(uid, gid, logger=logger),
                                cwd=path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                logger=logger)
    if process_handler.returncode is None or process_handler.returncode != 0:
      message = 'Failed to run buildout profile in directory %r' % path
      logger.error(message)
      raise BuildoutFailedError('%s:\n%s\n' % (message, process_handler.output))
  except OSError as exc:
    logger.exception(exc)
    raise BuildoutFailedError(exc)
  finally:
    old_umask = os.umask(umask)
    logger.debug('Restore umask from %03o to %03o' % (old_umask, umask))


def launchBuildout(path, buildout_binary, logger,
                   additional_buildout_parameter_list=None):
  """ Launches buildout."""
  if additional_buildout_parameter_list is None:
    additional_buildout_parameter_list = []
  # Reads uid/gid of path, launches buildout with thoses privileges
  stat_info = os.stat(path)
  uid = stat_info.st_uid
  gid = stat_info.st_gid
  # Extract python binary to prevent shebang size limit
  line = open(buildout_binary, 'r').readline()
  invocation_list = []
  if line.startswith('#!'):
    line = line[2:]
    # Prepares parameters for buildout
    invocation_list = line.split() + [buildout_binary]
  # Run buildout without reading user defaults
  invocation_list.append('-U')
  invocation_list.extend(additional_buildout_parameter_list)
  try:
    umask = os.umask(SAFE_UMASK)
    logger.debug('Set umask from %03o to %03o' % (umask, SAFE_UMASK))
    logger.debug('Invoking: %r in directory %r' % (' '.join(invocation_list),
      path))
    process_handler = SlapPopen(invocation_list,
                                preexec_fn=lambda: dropPrivileges(uid, gid, logger=logger),
                                cwd=path,
                                env=getCleanEnvironment(logger=logger,
                                                        home_path=path),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                logger=logger)
    if process_handler.returncode is None or process_handler.returncode != 0:
      message = 'Failed to run buildout profile in directory %r' % path
      logger.error(message)
      raise BuildoutFailedError('%s:\n%s\n' % (message, process_handler.output))
  except OSError as exc:
    logger.exception(exc)
    raise BuildoutFailedError(exc)
  finally:
    old_umask = os.umask(umask)
    logger.debug('Restore umask from %03o to %03o' % (old_umask, umask))


def updateFile(file_path, content, mode=0o600):
  """Creates or updates a file with "content" as content."""
  altered = False
  if not (os.path.isfile(file_path)) or \
     not (hashlib.md5(open(file_path).read()).digest() ==
          hashlib.md5(content).digest()):
    with open(file_path, 'w') as fout:
      fout.write(content)
    altered = True
  os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
  if stat.S_IMODE(os.stat(file_path).st_mode) != mode:
    os.chmod(file_path, mode)
    altered = True
  return altered


def updateExecutable(executable_path, content):
  """Creates or updates an executable file with "content" as content."""
  return updateFile(executable_path, content, 0o700)


def createPrivateDirectory(path):
  """Creates a directory belonging to root with umask 077"""
  if not os.path.isdir(path):
    os.mkdir(path)
  os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
  permission = stat.S_IMODE(os.stat(path).st_mode)
  if permission != 0o700:
    raise WrongPermissionError('Wrong permissions in %s: '
                               'is 0%o, should be 0700'
                               % (path, permission))

def killProcessTree(pid, logger):
  """
  kill all process Tree
  We first suspend processes to prevent them from reacting to signals
  """
  try:
    process = psutil.Process(pid)
    process.suspend()
  except psutil.Error:
    return

  process_list = [process]
  running_process_list = process.children(recursive=True)
  while running_process_list:
    process_list += running_process_list
    for child in running_process_list:
      try:
        child.suspend()
      except psutil.Error, e:
        logger.debug(str(e))

    time.sleep(0.2)
    running_process_list = set(process.children(recursive=True)).difference(process_list)

  for process in process_list:
    try:
      process.kill()
    except psutil.Error, e:
      logger.debug("Process kill: %s" % e)
