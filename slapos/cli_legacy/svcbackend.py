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

import logging
import os
from optparse import OptionParser
import ConfigParser

from slapos.grid.svcbackend import launchSupervisord

logger = logging.getLogger('SVCBackend')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)


def getOptionDict(*argument_tuple):
  usage = """
Typical usage:
 * %prog CONFIGURATION_FILE [arguments passed to supervisor]

""".strip()

  parser = OptionParser(usage=usage)

  # Parses arguments
  if argument_tuple:
    (argument_option_instance, argument_list) = parser.parse_args(list(argument_tuple))
  else:
    # No arguments given to entry point : we parse sys.argv.
    (argument_option_instance, argument_list) = parser.parse_args()

  if not argument_list:
    parser.error("Configuration file is obligatory. Consult documentation by calling with -h.")
  configuration_file = argument_list[0]
  if not os.path.exists(configuration_file):
    parser.error("Could not read configuration file : %s" % configuration_file)

  slapgrid_configuration = ConfigParser.SafeConfigParser()
  slapgrid_configuration.read(configuration_file)

  # Merges the two dictionnaries
  option_dict = dict(slapgrid_configuration.items("slapos"))
  # Supervisord configuration location
  option_dict.setdefault('supervisord_configuration_path',
                         os.path.join(option_dict['instance_root'], 'etc', 'supervisord.conf'))
  # Supervisord socket
  option_dict.setdefault('supervisord_socket',
                         os.path.join(option_dict['instance_root'], 'supervisord.socket'))
  return option_dict, argument_list[1:]


def supervisorctl(*argument_tuple):
  option_dict, args = getOptionDict(*argument_tuple)
  import supervisor.supervisorctl
  launchSupervisord(socket=option_dict['supervisord_socket'],
                    configuration_file=option_dict['supervisord_configuration_path'],
                    logger=logger)
  supervisor.supervisorctl.main(args=['-c', option_dict['supervisord_configuration_path']] + args)


def supervisord(*argument_tuple):
  option_dict, _ = getOptionDict(*argument_tuple)
  launchSupervisord(socket=option_dict['supervisord_socket'],
                    configuration_file=option_dict['supervisord_configuration_path'],
                    logger=logger)
