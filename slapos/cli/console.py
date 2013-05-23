# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, do_console, ClientConfig


class ConsoleCommand(ClientConfigCommand):
    """
    python console with slap library imported

    You can play with the global "slap" object and
    with the global "request" method.

    examples :
    >>> # Request instance
    >>> request(kvm, "myuniquekvm")
    >>> # Request software installation on owned computer
    >>> supply(kvm, "mycomputer")
    >>> # Fetch instance informations on already launched instance
    >>> request(kvm, "myuniquekvm").getConnectionParameter("url")
    """

    log = logging.getLogger('console')

    def get_parser(self, prog_name):
        ap = super(ConsoleCommand, self).get_parser(prog_name)

        ap.add_argument('-u', '--master_url',
                        help='Url of SlapOS Master to use')

        ap.add_argument('-k', '--key_file',
                        help='SSL Authorisation key file')

        ap.add_argument('-c', '--cert_file',
                        help='SSL Authorisation certificate file')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)
        local = init(conf)
        do_console(local)
