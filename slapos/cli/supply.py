# -*- coding: utf-8 -*-

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, ClientConfig


class SupplyCommand(ClientConfigCommand):
    """
    supply a Software to a node
    """

    def get_parser(self, prog_name):
        ap = super(SupplyCommand, self).get_parser(prog_name)

        ap.add_argument('software_url',
                        help='Your software url')

        ap.add_argument('node',
                        help='Target node')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)
        local = init(conf)
        do_supply(self.app.log, args.software_url, args.node, local)


def do_supply(logger, software_url, computer_id, local):
    """
    Request installation of Software Release
    'software_url' on computer 'computer_id'.
    """
    # XXX-Cedric Implement software_group support
    # XXX-Cedric Implement computer_group support
    logger.info('Requesting installation of %s Software Release...', software_url)

    if software_url in local:
        software_url = local[software_url]
    local['slap'].registerSupply().supply(
        software_release=software_url,
        computer_guid=computer_id,
        state='available'
    )
    logger.info('Done.')
