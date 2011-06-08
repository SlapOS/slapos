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

from supervisor import xmlrpc
import time
from utils import SlapPopen
import logging
import os
import sys
import xmlrpclib
from optparse import OptionParser
import ConfigParser
import socket as socketlib
import subprocess


def getSupervisorRPC(socket):
  supervisor_transport = xmlrpc.SupervisorTransport('', '',
      'unix://' + socket)
  server_proxy = xmlrpclib.ServerProxy('http://127.0.0.1',
      supervisor_transport)
  return getattr(server_proxy, 'supervisor')


def launchSupervisord(socket, configuration_file):
  logger = logging.getLogger('SVCBackend')
  supervisor = getSupervisorRPC(socket)
  if os.path.exists(socket):
    trynum = 1
    while trynum < 6:
      try:
        status = supervisor.getState()
      except xmlrpclib.Fault, e:
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
          logger.info('Supervisord already running.')
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
      executable=sys.executable, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  result = supervisord_popen.communicate()[0]
  if supervisord_popen.returncode == 0:
    log_message = 'Supervisord command invoked with: %s' % result
    logger.info(log_message)
    try:
      default_timeout = socketlib.getdefaulttimeout()
      current_timeout = 1
      trynum = 1
      while trynum < 6:
        try:
          socketlib.setdefaulttimeout(current_timeout)
          status = supervisor.getState()
          if status['statename'] == 'RUNNING' and status['statecode'] == 1:
            return
          logger.warning('Wrong status name %(statename)r and code '
            '%(statecode)r, trying again' % status)
          trynum += 1
        except Exception:
          current_timeout = 5 * trynum
          trynum += 1
          pass
        else:
          logger.info('Supervisord started correctly in try %s.' % trynum)
          return
      logger.warning('Issue while checking supervisord.')
    finally:
      socketlib.setdefaulttimeout(default_timeout)

  else:
    log_message = 'Supervisord unknown problem: %s' % result
    logger.warning(log_message)


def getOptionDict(*argument_tuple):
  usage = """
Typical usage:
 * %prog CONFIGURATION_FILE [arguments passed to supervisor]

""".strip()

  parser = OptionParser(usage=usage)
  # Parses arguments
  if argument_tuple == ():
    # No arguments given to entry point : we parse sys.argv.
    (argument_option_instance, argument_list) = parser.parse_args()
  else:
    (argument_option_instance, argument_list) = \
      parser.parse_args(list(argument_tuple))
  if len(argument_list) == 0:
    parser.error("Configuration file is obligatory. Consult documentation by "
        "calling with -h.")
  configuration_file = argument_list[0]
  if not os.path.exists(configuration_file):
    parser.error("Could not read configuration file : %s" \
        % configuration_file)
  slapgrid_configuration = ConfigParser.SafeConfigParser()
  slapgrid_configuration.read(configuration_file)
  # Merges the two dictionnaries
  option_dict = dict(slapgrid_configuration.items("slapos"))
  # Supervisord configuration location
  if not option_dict.get('supervisord_configuration_path'):
    option_dict['supervisord_configuration_path'] = \
      os.path.join(option_dict['instance_root'], 'etc', 'supervisord.conf')
  # Supervisord socket
  if not option_dict.get('supervisord_socket'):
    option_dict['supervisord_socket'] = \
      os.path.join(option_dict['instance_root'], 'supervisord.socket')
  return option_dict, argument_list[1:]


def supervisorctl(*argument_tuple):
  option_dict, args = getOptionDict(*argument_tuple)
  import supervisor.supervisorctl
  supervisor.supervisorctl.main(args=['-c',
    option_dict['supervisord_configuration_path']] + args)

def supervisord(*argument_tuple):
  option_dict, dummy = getOptionDict(*argument_tuple)
  dummy = dummy
  launchSupervisord(option_dict['supervisord_socket'],
      option_dict['supervisord_configuration_path'])
