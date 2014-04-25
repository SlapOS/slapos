# -*- coding: utf-8 -*-

import os

from slapos.cli.config import ConfigCommand
from slapos.grid.svcbackend import launchSupervisord


class SupervisordCommand(ConfigCommand):
    """
    launch, if not already running, supervisor daemon
    """
    command_group = 'node'

    def take_action(self, args):
        configp = self.fetch_config(args)
        instance_root = configp.get('slapos', 'instance_root')
        launchSupervisord(socket=os.path.join(instance_root, 'supervisord.socket'),
                          configuration_file=os.path.join(instance_root, 'etc', 'supervisord.conf'),
                          logger=self.app.log)
