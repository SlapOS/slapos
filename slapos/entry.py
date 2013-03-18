# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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

import argparse
import ConfigParser
import os
import sys
from slapos.bang import main as bang
from slapos.client import slapconsole as console
from slapos.client import request as request
from slapos.client import remove as remove
from slapos.client import supply as supply
from slapos.format import main as format
from slapos.cache import cache_lookup
from slapos.grid.slapgrid import runComputerPartition as instance
from slapos.grid.slapgrid import runSoftwareRelease as software
from slapos.grid.slapgrid import runUsageReport as report
from slapos.grid.svcbackend import supervisord
from slapos.grid.svcbackend import supervisorctl
from slapos.register.register import main as register
from slapos.version import version

# Note: this whole file is a hack. We should better try dedicated library
# like https://github.com/dhellmann/cliff or https://github.com/docopt/docopt.

GLOBAL_SLAPOS_CONFIGURATION = os.environ.get(
    'SLAPOS_CONFIGURATION',
    '/etc/opt/slapos/slapos.cfg')
USER_SLAPOS_CONFIGURATION = os.environ.get(
    'SLAPOS_CLIENT_CONFIGURATION',
    os.environ.get('SLAPOS_CONFIGURATION', '~/.slapos/slapos.cfg'))


class EntryPointNotImplementedError(NotImplementedError):
  def __init__(self, *args, **kw_args):
    NotImplementedError.__init__(self, *args, **kw_args)

def checkSlaposCfg():
  """
  Check if a slapos configuration file was given as a argument.
  If a slapos configuration file is given it return True else False
  """
  # XXX-Cedric: dangerous but quick way to achieve way to not provide
  # configuration file for each command without changing underlying code.
  # It the long term, it should be done in a better way (no guessing).
  for element in sys.argv:
    if '.cfg' in element:
      if os.path.exists(element):
        configuration = ConfigParser.SafeConfigParser()
        configuration.read(element)
        if configuration.has_section('slapos'):
          return True
  return False

def checkOption(option):
  """
  Check if a given option is already in call line
  Add it and its values if missing
  """
  option = option.split()
  key = option[0]
  for element in sys.argv:
    if key in element:
      return True
  sys.argv.append(key)
  if len(option) > 1 :
    sys.argv = sys.argv + option[1:]
  return True

def call(fun, config=False, option=None):
  """
  Add missing options to sys.argv
  Add config if asked and it is missing
  Call function fun
  """
  if option is None:
    option = []
  for element in option:
    checkOption(element)
  if config:
    if not checkSlaposCfg():
      sys.argv = [sys.argv[0]] + [os.path.expanduser(config)] + sys.argv[1:]
  fun()
  sys.exit(0)

def dispatch(command, is_node_command):
  """ Dispatch to correct SlapOS module.
  Here we could use introspection to get rid of the big "if" statements,
  but we want to control every input.
  Here we give default option and configuration file if they are needed, i.e
  If configuration file is not given: define it arbitrarily, and so on.
  """
  if is_node_command:

    if os.getuid() != 0:
      sys.stderr.write('This command must be run as root.\n')
      sys.exit()

    if command == 'register':
      call(register)
    elif command == 'software':
      call(software, config=GLOBAL_SLAPOS_CONFIGURATION,
           option=['--pidfile /opt/slapos/slapgrid-sr.pid'])
    elif command == 'instance':
      call(instance, config=GLOBAL_SLAPOS_CONFIGURATION,
           option=['--pidfile /opt/slapos/slapgrid-cp.pid'])
    elif command == 'report':
      call(report, config=GLOBAL_SLAPOS_CONFIGURATION,
           option=['--pidfile /opt/slapos/slapgrid-ur.pid'])
    elif command == 'bang':
      call(bang, config=True)
    elif command == 'format':
      call(format, config=GLOBAL_SLAPOS_CONFIGURATION, option=['-c', '-v'])
    elif command == 'supervisord':
      call(supervisord, config=GLOBAL_SLAPOS_CONFIGURATION)
    elif command == 'supervisorctl':
      call(supervisorctl, config=GLOBAL_SLAPOS_CONFIGURATION)
    elif command in ['start', 'stop', 'restart', 'status', 'tail']:
      # Again, too hackish
      sys.argv[-2:-2] = [command]
      call(supervisorctl, config=GLOBAL_SLAPOS_CONFIGURATION)
    else:
      return False
  elif command == 'request':
    call(request, config=USER_SLAPOS_CONFIGURATION)
  elif command == 'supply':
    call(supply, config=USER_SLAPOS_CONFIGURATION)
  elif command == 'remove':
    call(remove, config=USER_SLAPOS_CONFIGURATION)
  elif command == 'start':
    raise EntryPointNotImplementedError(command)
  elif command == 'stop':
    raise EntryPointNotImplementedError(command)
  elif command == 'destroy':
    raise EntryPointNotImplementedError(command)
  elif command == 'console':
    call(console, config=USER_SLAPOS_CONFIGURATION)
  elif command == 'cache-lookup':
    call(cache_lookup, config=GLOBAL_SLAPOS_CONFIGURATION)
  else:
    return False

def main():
  """
  Main entry point of SlapOS Node. Used to dispatch commands to python
  module responsible of the operation.
  """
  # If "node" arg is the first: we strip it and set a switch
  if len(sys.argv) > 1 and sys.argv[1] == "node":
    sys.argv.pop(1)
    # Hackish way to show status if no argument is specified
    if len(sys.argv) is 1:
      sys.argv.append('status')
    is_node = True
  else:
    is_node = False

  usage = """SlapOS %s command line interface.
For more informations, refer to SlapOS documentation.

Client subcommands usage:
  slapos request <instance-name> <software-url> [--configuration arg1=value1 arg2=value2 ... argN=valueN]
  slapos supply <software-url> <node-id>
  slapos console
  slapos cache-lookup <software-url-or-md5>
Node subcommands usage:
  slapos node
  slapos node register <node-id>
  slapos node software
  slapos node instance
  slapos node report
  slapos node format
  slapos node start <process>
  slapos node stop <process>
  slapos node restart <process>
  slapos node tail [process]
  slapos node status <process>
  slapos node supervisorctl
  slapos node supervisord
""" % version

  # Parse arguments
  # XXX remove the "positional arguments" from help message
  parser = argparse.ArgumentParser(usage=usage)
  parser.add_argument('command')
  parser.add_argument('argument_list', nargs=argparse.REMAINDER)

  namespace = parser.parse_args()
  # Set sys.argv for the sub-entry point that we will call
  command_line = [namespace.command]
  command_line.extend(namespace.argument_list)
  sys.argv = command_line

  try:
    if not dispatch(namespace.command, is_node):
      parser.print_help()
      sys.exit(1)
  except EntryPointNotImplementedError, exception:
    print ('The command %s does not exist or is not yet implemented. Please '
        'have a look at http://community.slapos.org to read documentation or '
        'forum. Please also make sure that SlapOS Node is up to '
        'date.' % exception)
    sys.exit(1)

