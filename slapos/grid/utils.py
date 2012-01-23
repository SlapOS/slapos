##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
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
import logging
import hashlib
import os
import pkg_resources
import stat
import subprocess
import sys
import pwd
import grp
from exception import BuildoutFailedError, WrongPermissionError
from hashlib import md5

# Such umask by default will create paths with full permission
# for user, non writable by group and not accessible by others
SAFE_UMASK = 027

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
  'ENV',
  'LOGNAME',
  'TEMP',
  'TMP',
  'TMPDIR',
  'USER',
]

LOCALE_ENVIRONEMNT_REMOVE_LIST = [
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

class AlreadyRunning(Exception):
  pass


class SlapPopen(subprocess.Popen):
  """Almost normal subprocess with gridish features"""
  def __init__(self, *args, **kwargs):
    kwargs.update(stdin=subprocess.PIPE)
    subprocess.Popen.__init__(self, *args, **kwargs)
    self.stdin.flush()
    self.stdin.close()
    self.stdin = None


def getSoftwareUrlHash(url):
  return md5(url).hexdigest()


def getCleanEnvironment(home_path='/tmp'):
  logger = logging.getLogger('CleanEnvironment')
  changed_env = {}
  removed_env = []
  env = os.environ.copy()
  # Clean python related environment variables
  for k in PYTHON_ENVIRONMENT_REMOVE_LIST + SYSTEM_ENVIRONMENT_REMOVE_LIST \
      + LOCALE_ENVIRONEMNT_REMOVE_LIST:
    old = env.pop(k, None)
    if old is not None:
      removed_env.append(k)
  changed_env['HOME'] = env['HOME'] = home_path
  for k in sorted(changed_env.iterkeys()):
    logger.debug('Overriden %s = %r' % (k,changed_env[k]))
  logger.debug('Removed from environement: %s' % ', '.join(sorted(removed_env)))
  return env


def setRunning(pid_file):
  """Creates a pidfile. If a pidfile already exists, we exit"""
  logger = logging.getLogger('Slapgrid')
  if os.path.exists(pid_file):
    # Pid file is present
    logger.warning('pid file already exists : %s' % (pid_file))
    try:
      pid = int(open(pid_file, 'r').readline())
    except ValueError:
      pid = None
    # XXX This could use psutil library.
    if pid is not None and os.path.exists("/proc/%s" % pid):
      #XXX: can we trust sys.argv?
      process_name = os.path.basename(sys.argv[0])
      if process_name in open('/proc/%s/cmdline' % pid, 'r').readline():
        # In case process is present, ignore.
        raise AlreadyRunning('A slapgrid process is running with pid %s' % pid)
    logger.info('Pid file %r was stale one, overwritten' % pid_file)
  # Start new process
  write_pid(pid_file)


def setFinished(pid_file):
  try:
    os.remove(pid_file)
  except OSError:
    pass


def write_pid(pid_file):
  logger = logging.getLogger('Slapgrid')
  pid = os.getpid()
  try:
    f = open(pid_file, 'w')
    f.write('%s' % pid)
    f.close()
  except (IOError, OSError):
    logger.critical('slapgrid could not write pidfile %s' % pid_file)
    raise


def dropPrivileges(uid, gid):
  """Drop privileges to uid, gid if current uid is 0

  Do tests to check if dropping was successful and that no system call is able
  to re-raise dropped privileges

  Does nothing in case if uid and gid are not 0
  """
  logger = logging.getLogger('dropPrivileges')
  current_uid, current_gid = os.getuid(), os.getgid()
  if uid == 0 or gid == 0:
    raise OSError('Dropping privileges to uid = %r or ' \
                                      'gid = %r is too dangerous' % (uid, gid))
  if not(current_uid == 0 and current_gid == 0):
    logger.debug('Running as uid = %r, gid = %r, dropping not needed and not '
        'possible' % (current_uid, current_gid))
    return
  # drop privileges
  user_name = pwd.getpwuid(uid)[0]
  group_list = set([x.gr_gid for x in grp.getgrall() if user_name in x.gr_mem])
  group_list.add(gid)
  os.initgroups(pwd.getpwuid(uid)[0], gid)
  os.setgid(gid)
  os.setuid(uid)

  # assert that privileges are dropped
  message_pre = 'After dropping to uid = %r and gid = %r ' \
                'and group_list = %s' % (
                            uid, gid, group_list)
  new_uid, new_gid, new_group_list = os.getuid(), os.getgid(), os.getgroups()
  if not (new_uid == uid and new_gid == gid and set(new_group_list) == group_list):
    raise OSError('%s new_uid = %r and new_gid = %r and ' \
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
        '%r which is fatal.' % message_pre, current_uid, current_gid)
  logger.info('Succesfully dropped privileges to uid=%r gid=%r' % (uid, gid))


def bootstrapBuildout(path, buildout=None,
    additional_buildout_parametr_list=None, console=False):
  if additional_buildout_parametr_list is None:
    additional_buildout_parametr_list = []
  logger = logging.getLogger('BuildoutManager')
  # Reads uid/gid of path, launches buildout with thoses privileges
  stat_info = os.stat(path)
  uid = stat_info.st_uid
  gid = stat_info.st_gid

  invocation_list = [sys.executable, '-S']
  kw = dict()
  if buildout is not None:
    invocation_list.append(buildout)
    invocation_list.extend(additional_buildout_parametr_list)
  else:
    try:
      import zc.buildout
    except ImportError:
      logger.warning('Using old style bootstrap of included bootstrap file. '
        'Consider having zc.buildout available in search path.')
      invocation_list.append(pkg_resources.resource_filename(__name__,
        'zc.buildout-bootstap.py'))
      invocation_list.extend(additional_buildout_parametr_list)
    else:
      # buildout is importable, so use this one
      invocation_list.extend(["-c", "import sys ; sys.path=" + str(sys.path) +
        " ; import zc.buildout.buildout ; sys.argv[1:1]=" + \
        repr(additional_buildout_parametr_list + ['bootstrap']) + " ; "
        "zc.buildout.buildout.main()"])

  if buildout is not None:
    invocation_list.append('bootstrap')
  try:
    umask = os.umask(SAFE_UMASK)
    logger.debug('Set umask from %03o to %03o' % (umask, SAFE_UMASK))
    logger.debug('Invoking: %r in directory %r' % (' '.join(invocation_list),
      path))
    if not console:
      kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process_handler = SlapPopen(invocation_list,
            preexec_fn=lambda: dropPrivileges(uid, gid),
            cwd=path, **kw)
    result = process_handler.communicate()[0]
    if console:
      result = 'Please consult messages above'
    if process_handler.returncode is None or process_handler.returncode != 0:
      message = 'Failed to run buildout profile in directory %r:\n%s\n' % (
          path, result)
      raise BuildoutFailedError(message)
    else:
      logger.debug('Successful run:\n%s' % result)
  except OSError as error:
    raise BuildoutFailedError(error)
  finally:
    old_umask = os.umask(umask)
    logger.debug('Restore umask from %03o to %03o' % (old_umask, umask))


def launchBuildout(path, buildout_binary,
                   additional_buildout_parametr_list=None, console=False):
  """ Launches buildout."""
  logger = logging.getLogger('BuildoutManager')
  if additional_buildout_parametr_list is None:
    additional_buildout_parametr_list = []
  # Reads uid/gid of path, launches buildout with thoses privileges
  stat_info = os.stat(path)
  uid = stat_info.st_uid
  gid = stat_info.st_gid
  # Extract python binary to prevent shebang size limit
  file = open(buildout_binary, 'r')
  line = file.readline()
  file.close()
  invocation_list = []
  if line.startswith('#!'):
    line = line[2:]
    # Prepares parameters for buildout
    invocation_list = line.split() + [buildout_binary]
  # Run buildout without reading user defaults
  invocation_list.append('-U')
  invocation_list.extend(additional_buildout_parametr_list)
  try:
    umask = os.umask(SAFE_UMASK)
    logger.debug('Set umask from %03o to %03o' % (umask, SAFE_UMASK))
    logger.debug('Invoking: %r in directory %r' % (' '.join(invocation_list),
      path))
    kw = dict()
    if not console:
      kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process_handler = SlapPopen(invocation_list,
            preexec_fn=lambda: dropPrivileges(uid, gid), cwd=path,
            env=getCleanEnvironment(pwd.getpwuid(uid).pw_dir), **kw)
    result = process_handler.communicate()[0]
    if console:
      result = 'Please consult messages above'
    if process_handler.returncode is None or process_handler.returncode != 0:
      message = 'Failed to run buildout profile in directory %r:\n%s\n' % (
          path, result)
      raise BuildoutFailedError(message)
    else:
      logger.debug('Successful run:\n%s' % result)
  except OSError as error:
    raise BuildoutFailedError(error)
  finally:
    old_umask = os.umask(umask)
    logger.debug('Restore umask from %03o to %03o' % (old_umask, umask))


def updateFile(file_path, content, mode='0600'):
  """Creates an executable with "content" as content."""
  altered = False
  if not (os.path.isfile(file_path)) or \
    not(hashlib.md5(open(file_path).read()).digest() ==\
        hashlib.md5(content).digest()):
      altered = True
      file_file = open(file_path, 'w')
      file_file.write(content)
      file_file.flush()
      file_file.close()
  os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
  if oct(stat.S_IMODE(os.stat(file_path).st_mode)) != mode:
    os.chmod(file_path, int(mode, 8))
    altered = True
  return altered


def updateExecutable(executable_path, content):
  """Creates an executable with "content" as content."""
  return updateFile(executable_path, content, '0700')


def createPrivateDirectory(path):
  """Creates directory belonging to root with umask 077"""
  if not os.path.isdir(path):
    os.mkdir(path)
  os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
  permission = oct(stat.S_IMODE(os.stat(path).st_mode))
  if permission not in ('0700'):
    raise WrongPermissionError('Wrong permissions in %s ' \
                                        ': is %s, should be 0700'
                                        % path, permission)
