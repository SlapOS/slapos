# -*- coding: utf-8 -*-

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
