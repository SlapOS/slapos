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

import os
import pkg_resources
import socket as socketlib
import subprocess
import stat
import sys
import time
import xmlrpclib

from slapos.grid.utils import (createPrivateDirectory, SlapPopen, updateFile)

from supervisor import xmlrpc, states


def getSupervisorRPC(socket):
  supervisor_transport = xmlrpc.SupervisorTransport('', '',
      'unix://' + socket)
  server_proxy = xmlrpclib.ServerProxy('http://127.0.0.1',
      supervisor_transport)
  return getattr(server_proxy, 'supervisor')


def _getSupervisordSocketPath(instance_root):
  return os.path.join(instance_root, 'supervisord.socket')

def _getSupervisordConfigurationFilePath(instance_root):
  return os.path.join(instance_root, 'etc', 'supervisord.conf')

def _getSupervisordConfigurationDirectory(instance_root):
  return os.path.join(instance_root, 'etc', 'supervisord.conf.d')

def createSupervisordConfiguration(instance_root, watchdog_command=''):
  """
  Create supervisord related files and directories.
  """
  if not os.path.isdir(instance_root):
    raise OSError('%s does not exist.' % instance_root)

  supervisord_configuration_file_path = _getSupervisordConfigurationFilePath(instance_root)
  supervisord_configuration_directory = _getSupervisordConfigurationDirectory(instance_root)
  supervisord_socket = _getSupervisordSocketPath(instance_root)

  # Create directory accessible for the instances.
  var_directory = os.path.join(instance_root, 'var')
  if not os.path.isdir(var_directory):
    os.mkdir(var_directory)
  os.chmod(var_directory, stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH | \
                          stat.S_IRGRP | stat.S_IXGRP )
  etc_directory = os.path.join(instance_root, 'etc')
  if not os.path.isdir(etc_directory):
    os.mkdir(etc_directory)

  # Creates instance_root structure
  createPrivateDirectory(os.path.join(instance_root, 'var', 'log'))
  createPrivateDirectory(os.path.join(instance_root, 'var', 'run'))

  createPrivateDirectory(os.path.join(instance_root, 'etc'))
  createPrivateDirectory(supervisord_configuration_directory)

  # Creates supervisord configuration
  updateFile(supervisord_configuration_file_path,
    pkg_resources.resource_stream(__name__,
      'templates/supervisord.conf.in').read() % {
          'supervisord_configuration_directory': supervisord_configuration_directory,
          'supervisord_socket': os.path.abspath(supervisord_socket),
          'supervisord_loglevel': 'info',
          'supervisord_logfile': os.path.abspath(
              os.path.join(instance_root, 'var', 'log', 'supervisord.log')),
          'supervisord_logfile_maxbytes': '50MB',
          'supervisord_nodaemon': 'false',
          'supervisord_pidfile': os.path.abspath(
              os.path.join(instance_root, 'var', 'run', 'supervisord.pid')),
          'supervisord_logfile_backups': '10',
          # Do not set minfds. select() does not support file descriptors
          # greater than 1023.
          # 'supervisord_minfds': '4096',
          'watchdog_command': watchdog_command,
      }
  )

def _updateWatchdog(socket):
  """
  In special cases, supervisord can be started using configuration
  with empty watchdog parameter.
  Then, when running slapgrid, the real watchdog configuration is generated.
  We thus need to reload watchdog configuration if needed and start it.
  """
  supervisor = getSupervisorRPC(socket)
  if supervisor.getProcessInfo('watchdog')['state'] not in states.RUNNING_STATES:
    # XXX workaround for https://github.com/Supervisor/supervisor/issues/339
    # In theory, only reloadConfig is needed.
    supervisor.removeProcessGroup('watchdog')
    supervisor.reloadConfig()
    supervisor.addProcessGroup('watchdog')

def launchSupervisord(instance_root, logger,
                      supervisord_additional_argument_list=None):
  configuration_file = _getSupervisordConfigurationFilePath(instance_root)
  socket = _getSupervisordSocketPath(instance_root)
  if os.path.exists(socket):
    trynum = 1
    while trynum < 6:
      try:
        supervisor = getSupervisorRPC(socket)
        status = supervisor.getState()
      except xmlrpclib.Fault as e:
        if e.faultCode == 6 and e.faultString == 'SHUTDOWN_STATE':
          logger.info('Supervisor in shutdown procedure, will check again later.')
          trynum += 1
          time.sleep(2 * trynum)
      except Exception:
        # In case if there is problem with connection, assume that supervisord
        # is not running and try to run it
        break
      else:
        if status['statename'] == 'RUNNING' and status['statecode'] == 1:
          logger.debug('Supervisord already running.')
          _updateWatchdog(socket)
          return
        elif status['statename'] == 'SHUTDOWN_STATE' and status['statecode'] == 6:
          logger.info('Supervisor in shutdown procedure, will check again later.')
          trynum += 1
          time.sleep(2 * trynum)
        else:
          log_message = 'Unknown supervisord state %r. Will try to start.' % status
          logger.warning(log_message)
          break

  supervisord_argument_list = ['-c', configuration_file]
  if supervisord_additional_argument_list is not None:
    supervisord_argument_list.extend(supervisord_additional_argument_list)

  logger.info("Launching supervisord with clean environment.")
  # Extract python binary to prevent shebang size limit
  invocation_list = [sys.executable, '-c']
  invocation_list.append(
      "import sys ; sys.path=" + str(sys.path) + " ; " +
      "import supervisor.supervisord ; " +
      "sys.argv[1:1]=" + str(supervisord_argument_list) + " ; " +
      "supervisor.supervisord.main()")
  supervisord_popen = SlapPopen(invocation_list,
                                env={},
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                logger=logger)

  result = supervisord_popen.communicate()[0]
  if supervisord_popen.returncode:
    logger.warning('Supervisord unknown problem: %s' % result)
    raise RuntimeError('Failed to launch supervisord : %s' % result)

  try:
    default_timeout = socketlib.getdefaulttimeout()
    current_timeout = 1
    trynum = 1
    while trynum < 6:
      try:
        socketlib.setdefaulttimeout(current_timeout)
        supervisor = getSupervisorRPC(socket)
        status = supervisor.getState()
        if status['statename'] == 'RUNNING' and status['statecode'] == 1:
          return
        logger.warning('Wrong status name %(statename)r and code '
          '%(statecode)r, trying again' % status)
        trynum += 1
      except Exception:
        current_timeout = 5 * trynum
        trynum += 1
      else:
        logger.info('Supervisord started correctly in try %s.' % trynum)
        return
    logger.warning('Issue while checking supervisord.')
  finally:
    socketlib.setdefaulttimeout(default_timeout)

