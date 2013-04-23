# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, do_remove, ClientConfig


class RemoveCommand(ClientConfigCommand):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        ap = super(RemoveCommand, self).get_parser(prog_name)

        ap.add_argument('software_url',
                        help='Your software url')

        ap.add_argument('none',
                        help="Target node")

        return ap

    def take_action(self, args):
        configuration_parser = self.fetch_config(args)
        config = ClientConfig(args, configuration_parser)
        local = init(config)
        do_remove(args.software_url, args.node, local)
