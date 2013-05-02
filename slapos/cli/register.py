# -*- coding: utf-8 -*-

import logging
import sys

from slapos.cli.command import Command
from slapos.register.register import do_register, RegisterConfig


class RegisterCommand(Command):
    """
    register a node in the SlapOS cloud
    """

    log = logging.getLogger('Register')

    def get_parser(self, prog_name):
        ap = super(RegisterCommand, self).get_parser(prog_name)

        ap.add_argument('node_name',
                        help='Name of the node')

        ap.add_argument('--interface-name',
                        help='Interface name to access internet',
                        default='eth0')

        ap.add_argument('--master-url',
                        help='URL of SlapOS master',
                        default='https://slap.vifib.com')

        ap.add_argument('--master-url-web',
                        help='URL of SlapOS Master webservice to register certificates',
                        default='https://www.slapos.org')

        ap.add_argument('--partition-number',
                        help='Number of partition on computer',
                        default='10',
                        type=int)

        ap.add_argument('--ipv4-local-network',
                        help='Base of ipv4 local network',
                        default='10.0.0.0/16')

        ap.add_argument('--ipv6-interface',
                        help='Interface name to get ipv6',
                        default='')

        ap.add_argument('--login',
                        help='User login on SlapOS Master webservice')

        ap.add_argument('--password',
                        help='User password on SlapOs Master webservice')

        ap.add_argument('-t', '--create-tap',
                        help='Will trigger creation of one virtual "tap" interface per '
                             'Partition and attach it to primary interface. Requires '
                             'primary interface to be a bridge. defaults to false. '
                             'Needed to host virtual machines.',
                        default=False,
                        action='store_true')

        ap.add_argument('-n', '--dry-run',
                        help='Simulate the execution steps',
                        default=False,
                        action='store_true')

        return ap

    def take_action(self, args):
        try:
            conf = RegisterConfig(logger=self.log)
            conf.setConfig(args)
            return_code = do_register(conf)
        except SystemExit as err:
            return_code = err

        sys.exit(return_code)
