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
import os
import sys

def runTestSuite(args, d):
  env = os.environ.copy()
  if 'openssl_binary' in d:
    env['OPENSSL_BINARY'] = d['openssl_binary']
  if 'test_ca_path' in d:
    env['TEST_CA_PATH'] = d['test_ca_path']
  if 'prepend_path' in d:
    try:
      env['PATH'] = d['prepend_path'] + ':' + env['PATH']
    except KeyError:
      env['PATH'] = d['prepend_path']
  if 'instance_home' in d:
    env['INSTANCE_HOME'] = d['instance_home']
    env['REAL_INSTANCE_HOME'] = d['instance_home']

  # If defined, will add (and replace if existing) envvars to environment.
  if 'environment' in d:
    env.update(d['environment'])

  # Deal with Shebang size limitation
  executable_filepath = args[0]
  with open(executable_filepath, 'r') as f:
    line = f.readline()
  argument_list = []
  if line[:2] == '#!':
    executable_filepath = line[2:].strip()
    argument_list.append(executable_filepath)
  argument_list += args
  argument_list += sys.argv[1:]
  os.execve(executable_filepath, argument_list, env)

runUnitTest = runTestSuite
