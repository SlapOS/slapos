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

import time
import os
import sys
import xmlrpclib
import socket as socketlib
import subprocess

from supervisor import xmlrpc
from slapos.grid.utils import SlapPopen


def getSupervisorRPC(socket):
  supervisor_transport = xmlrpc.SupervisorTransport('', '',
      'unix://' + socket)
  server_proxy = xmlrpclib.ServerProxy('http://127.0.0.1',
      supervisor_transport)
  return getattr(server_proxy, 'supervisor')


def launchSupervisord(socket, configuration_file, logger):
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
      except Exception as e:
        # In case if there is problem with connection, assume that supervisord
        # is not running and try to run it
        break
      else:
        if status['statename'] == 'RUNNING' and status['statecode'] == 1:
          logger.debug('Supervisord already running.')
          return
        elif status['statename'] == 'SHUTDOWN_STATE' and status['statecode'] == 6:
          logger.info('Supervisor in shutdown procedure, will check again later.')
          trynum += 1
          time.sleep(2 * trynum)
        else:
          log_message = 'Unknown supervisord state %r. Will try to start.' % status
          logger.warning(log_message)
          break

  logger.info("Launching supervisord with clean environment.")
  # Extract python binary to prevent shebang size limit
  invocation_list = ["supervisord", '-c']
  invocation_list.append("import sys ; sys.path=" + str(sys.path) + " ; import "
      "supervisor.supervisord ; sys.argv[1:1]=['-c','" +
      configuration_file +
      "'] ; supervisor.supervisord.main()")
  supervisord_popen = SlapPopen(invocation_list,
                                env={},
                                executable=sys.executable,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                logger=logger)

  result = supervisord_popen.communicate()[0]
  if supervisord_popen.returncode:
    logger.warning('Supervisord unknown problem: %s' % result)
    return

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
      except Exception as e:
        current_timeout = 5 * trynum
        trynum += 1
      else:
        logger.info('Supervisord started correctly in try %s.' % trynum)
        return
    logger.warning('Issue while checking supervisord.')
  finally:
    socketlib.setdefaulttimeout(default_timeout)
