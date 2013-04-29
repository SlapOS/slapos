# -*- coding: utf-8 -*-

import logging
import os

from slapos.cli.config import ConfigCommand
from slapos.grid.svcbackend import launchSupervisord


class SupervisordCommand(ConfigCommand):

    log = logging.getLogger(__name__)

    def take_action(self, args):
        config = self.fetch_config(args)
        instance_root = config.get('slapos', 'instance_root')
        launchSupervisord(socket=os.path.join(instance_root, 'supervisord.socket'),
                          configuration_file=os.path.join(instance_root, 'etc', 'supervisord.conf'),
                          logger=self.log)
