# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ConfigCommand
from slapos.proxy import do_proxy, ProxyConfig


class ProxyCommand(ConfigCommand):
    """
    minimalist, stand-alone SlapOS Master
    """

    log = logging.getLogger('proxy')

    def get_parser(self, prog_name):
        ap = super(ProxyCommand, self).get_parser(prog_name)

        ap.add_argument('-u', '--database-uri',
                        help='URI for sqlite database')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)

        conf = ProxyConfig(logger=self.log)

        conf.mergeConfig(args, configp)

        if not self.app.options.log_file and hasattr(conf, 'log_file'):
            # no log file is provided by argparser,
            # we set up the one from config
            file_handler = logging.FileHandler(conf.log_file)
            formatter = logging.Formatter(self.app.LOG_FILE_MESSAGE_FORMAT)
            file_handler.setFormatter(formatter)
            self.log.addHandler(file_handler)

        conf.setConfig()

        do_proxy(conf=conf)

