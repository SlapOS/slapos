# -*- coding: utf-8 -*-

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, ClientConfig, _getSoftwareReleaseFromSoftwareString

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
        local = init(conf, self.app.log)
        do_supply(self.app.log, args.software_url, args.node, local)


def do_supply(logger, software_release, computer_id, local):
    """
    Request installation of Software Release
    'software_release' on computer 'computer_id'.
    """
    logger.info('Requesting software installation of %s...',
                software_release)

    software_release = _getSoftwareReleaseFromSoftwareString(
        logger, software_release, local['product'])

    local['supply'](
        software_release=software_release,
        computer_guid=computer_id,
        state='available'
    )
    logger.info('Done.')
