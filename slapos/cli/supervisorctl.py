# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import argparse
import os

from slapos.cli.command import check_root_user
from slapos.cli.config import ConfigCommand
from slapos.grid.svcbackend import launchSupervisord

from slapos.util import string_to_boolean

import supervisor.supervisorctl


class SupervisorctlCommand(ConfigCommand):
    """
    open supervisor console, for process management
    """
    command_group = 'node'

    def get_parser(self, prog_name):
        ap = super(SupervisorctlCommand, self).get_parser(prog_name)
        ap.add_argument('supervisor_args',
                        nargs=argparse.REMAINDER,
                        help='parameters passed to supervisorctl')
        return ap

    def _should_check_current_user_is_root(self, configp):
      if not configp.has_option('slapos', 'root_check'):
        return True
      return configp.getboolean('slapos', 'root_check')

    def take_action(self, args):
        configp = self.fetch_config(args)

        # Parse if we have to check if running from root
        # XXX document this feature.
        if self._should_check_current_user_is_root(configp):
          check_root_user(self)

        instance_root = configp.get('slapos', 'instance_root')
        configuration_file = os.path.join(instance_root, 'etc', 'supervisord.conf')
        launchSupervisord(socket=os.path.join(instance_root, 'supervisord.socket'),
                          configuration_file=configuration_file,
                          logger=self.app.log)
        supervisor.supervisorctl.main(args=['-c', configuration_file] + args.supervisor_args)


class SupervisorctlAliasCommand(SupervisorctlCommand):
    def take_action(self, args):
        args.supervisor_args = [self.alias] + args.supervisor_args
        super(SupervisorctlAliasCommand, self).take_action(args)


class SupervisorctlStatusCommand(SupervisorctlAliasCommand):
    """alias for 'node supervisorctl status'"""
    alias = 'status'


class SupervisorctlStartCommand(SupervisorctlAliasCommand):
    """alias for 'node supervisorctl start'"""
    alias = 'start'


class SupervisorctlStopCommand(SupervisorctlAliasCommand):
    """alias for 'node supervisorctl stop'"""
    alias = 'stop'


class SupervisorctlRestartCommand(SupervisorctlAliasCommand):
    """alias for 'node supervisorctl restart'"""
    alias = 'restart'


class SupervisorctlTailCommand(SupervisorctlAliasCommand):
    """alias for 'node supervisorctl tail'"""
    alias = 'tail'
