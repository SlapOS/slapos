# -*- coding: utf-8 -*-

import logging
import sys

from slapos.cli.command import Command, must_be_root
from slapos.register.register import do_register, RegisterConfig


class RegisterCommand(Command):
    """
    register a node in the SlapOS cloud
    """

    log = logging.getLogger('register')

    def get_parser(self, prog_name):
        ap = super(RegisterCommand, self).get_parser(prog_name)

        ap.add_argument('node_name',
                        help='Name of the node')

        ap.add_argument('--interface-name',
                        default='eth0',
                        help='Primary network interface. IP of Partitions '
                             'will be added to it'
                             ' (default: %(default)s)')

        ap.add_argument('--master-url',
                        default='https://slap.vifib.com',
                        help='URL of SlapOS Master REST API'
                             ' (default: %(default)s)')

        ap.add_argument('--master-url-web',
                        default='https://www.slapos.org',
                        help='URL of SlapOS Master webservice to register certificates'
                             ' (default: %(default)s)')

        ap.add_argument('--partition-number',
                        default=10,
                        type=int,
                        help='Number of partitions to create in the SlapOS Node'
                             ' (default: %(default)s)')

        ap.add_argument('--ipv4-local-network',
                        default='10.0.0.0/16',
                        help='Subnetwork used to assign local IPv4 addresses. '
                             'It should be a not used network in order to avoid conflicts'
                             ' (default: %(default)s)')

        ap.add_argument('--ipv6-interface',
                        help='Interface name to get ipv6')

        ap.add_argument('--login-auth',
                        action='store_true',
                        help='Force login and password authentication')

        ap.add_argument('--login',
                        help='Your SlapOS Master login. '
                             'Asks it interactively, then password.')

        ap.add_argument('--password',
                        help='Your SlapOS Master password. If not provided, '
                             'asks it interactively. NOTE: giving password as parameter '
                             'should be avoided for security reasons.')

        ap.add_argument('--token',
                        help="SlapOS 'computer security' authentication token")

        ap.add_argument('-t', '--create-tap',
                        action='store_true',
                        help='Will trigger creation of one virtual "tap" interface per '
                             'Partition and attach it to primary interface. Requires '
                             'primary interface to be a bridge. '
                             'Needed to host virtual machines'
                             ' (default: %(default)s)')

        ap.add_argument('-n', '--dry-run',
                        action='store_true',
                        help='Simulate the execution steps'
                             ' (default: %(default)s)')

        return ap

    @must_be_root
    def take_action(self, args):
        try:
            conf = RegisterConfig(logger=self.log)
            conf.setConfig(args)
            return_code = do_register(conf)
        except SystemExit as err:
            return_code = err

        sys.exit(return_code)
