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
from slapos.console import run as console
from slapos.console import request as request
from slapos.format import main as format
from slapos.grid.slapgrid import runComputerPartition as instance
from slapos.grid.slapgrid import runSoftwareRelease as software
from slapos.grid.slapgrid import runUsageReport as report
from slapos.grid.svcbackend import supervisord
from slapos.grid.svcbackend import supervisorctl
from slapos.register.register import main as register

class EntryPointNotImplementedError(NotImplementedError):
  def __init__(self, *args, **kw_args):
    NotImplementedError.__init__(self, *args, **kw_args)

def checkSlaposCfg ():
  """
  Check if a slapos configuration file was given as a argument.
  If a slapos configuration file is given it return True else False
  """
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

def call(fun, config=False, option=[]):
  """
  Add missing options to sys.argv
  Add config if asked and it is missing
  Call function fun
  """
  for element in option:
    checkOption(element)
  if config:
    if not checkSlaposCfg():
      sys.argv.append(config)
  fun()

def showUsage():
  # We are out of option. We have to admit it: no other option than error.
  # XXX Real error message
  sys.exit(1)

def dispatch(command, is_node):
  """ Dispatch to correct SlapOS module.
  Here we could use introspection to get rid of the big "if" statements,
  but we want to control every input.
  Here we give default option and configuration file if they are needed
  """
  # XXX console_config =
  if is_node:
    config = '/etc/opt/slapos/slapos.cfg'
    if command in 'register':
      call(register)
    elif command == 'software':
      call(software, config=config,
           option=['--logfile /opt/slapos/slapgrid-sr.log',
                   '--pidfile /opt/slapos/slapgrid-sr.pid'])
    elif command == 'instance':
      call(instance, config=config,
           option=['--logfile /opt/slapos/slapgrid-cp.log',
                   '--pidfile /opt/slapos/slapgrid-cp.pid'])
    elif command == 'report':
      call(report, config=config,
           option=['--logfile /opt/slapos/slapgrid-ur.log'])
    elif command == 'bang':
      call(bang, config=True)
    elif command == 'format':
      call(format, config=config,
           option=['--log_file /opt/slapos/slapformat.log'])
    elif command in ['start', 'stop', 'status', 'tail']:
      supervisord()
      supervisorctl()
    else:
      supervisord()
  elif command == 'request':
    request()
  elif command == 'supply':
    raise EntryPointNotImplementedError(command)
  elif command == 'start':
    raise EntryPointNotImplementedError(command)
  elif command == 'stop':
    raise EntryPointNotImplementedError(command)
  elif command == 'console':
    console()
  else:
    return False

def main():
  """
  Main entry point of SlapOS Node. Used to dispatch commands to python
  module responsible of the operation.
  """
  description = "XXX TODO"
  # Parse arguments
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('command')
  parser.add_argument('argument_list', nargs=argparse.REMAINDER)

  # If "node" arg is the first: we strip it and set a switch
  # XXX do it with argparse
  if len(sys.argv) > 1 and sys.argv[1] == "node":
    sys.argv=sys.argv[1:]
    is_node = True
  else:
    is_node = False

  namespace = parser.parse_args()
  # Set sys.argv for the sub-entry point that we will call
  command_line = [namespace.command]
  command_line.extend(namespace.argument_list)
  sys.argv = command_line

  dispatch(namespace.command,is_node)
  # If configuration file is not given: define it arbitrarily
  # If client commands: use ~/.slapos.cfg
  # If node commands: use /etc/opt/slapos/slapos.cfg
  # XXX TODO
  try:
    if not dispatch(namespace.command, is_node):
      parser.print_help()
  except EntryPointNotImplementedError, exception:
    # XXX more graceful
    print 'Not implemented: %s' % exception
