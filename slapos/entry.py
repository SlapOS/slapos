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
from slapos.client import run as console
from slapos.client import request as request
from slapos.format import main as format
from slapos.grid.slapgrid import runComputerPartition as instance
from slapos.grid.slapgrid import runSoftwareRelease as software
from slapos.grid.slapgrid import runUsageReport as report
from slapos.grid.svcbackend import supervisord
from slapos.grid.svcbackend import supervisorctl
from slapos.register.register import main as register

GLOBAL_SLAPOS_CONFIGURATION = '/etc/opt/slapos/slapos.cfg'
USER_SLAPOS_CONFIGURATION = '~/.slapos/slapos.cfg'

class EntryPointNotImplementedError(NotImplementedError):
  def __init__(self, *args, **kw_args):
    NotImplementedError.__init__(self, *args, **kw_args)

def checkSlaposCfg ():
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
      sys.argv = [sys.argv[0]] + [config] + sys.argv[1:]
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
      call(format, config=GLOBAL_SLAPOS_CONFIGURATION)
    elif command in ['start', 'stop', 'status', 'tail']:
      supervisord()
      supervisorctl()
    else:
      return False
  elif command == 'request':
    call(request, config=USER_SLAPOS_CONFIGURATION)
  elif command == 'supply':
    raise EntryPointNotImplementedError(command)
  elif command == 'start':
    raise EntryPointNotImplementedError(command)
  elif command == 'stop':
    raise EntryPointNotImplementedError(command)
  elif command == 'console':
    call(console, config=USER_SLAPOS_CONFIGURATION)
  else:
    return False

def main():
  """
  Main entry point of SlapOS Node. Used to dispatch commands to python
  module responsible of the operation.
  """
  # XXX-Cedric: add "description" for parser.
  # Parse arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('command')
  # XXX-Cedric: "slapos node" should display "supervisorctl status".
  # Currently it does nothing
  parser.add_argument('argument_list', nargs=argparse.REMAINDER)

  # If "node" arg is the first: we strip it and set a switch
  if len(sys.argv) > 1 and sys.argv[1] == "node":
    sys.argv = sys.argv[1:]
    is_node = True
  else:
    is_node = False

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
    print 'Not yet implemented: %s. Please use old-style commands.' % exception
