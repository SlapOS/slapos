# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, ClientConfig


class RemoveCommand(ClientConfigCommand):
    """
    remove a Software from a node
    """

    log = logging.getLogger('remove')

    def get_parser(self, prog_name):
        ap = super(RemoveCommand, self).get_parser(prog_name)

        ap.add_argument('software_url',
                        help='Your software url')

        ap.add_argument('node',
                        help="Target node")

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)
        local = init(conf)
        do_remove(self.app.log, args.software_url, args.node, local)


def do_remove(logger, software_url, computer_id, local):
    """
    Request deletion of Software Release
    'software_url' from computer 'computer_id'.
    """
    logger.info('Requesting deletion of %s Software Release...', software_url)

    if software_url in local:
        software_url = local[software_url]
    local['slap'].registerSupply().supply(
        software_release=software_url,
        computer_guid=computer_id,
        state='destroyed'
    )
    logger.info('Done.')
