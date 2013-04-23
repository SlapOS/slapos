# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, do_console, ClientConfig


class ConsoleCommand(ClientConfigCommand):
    """
    slapconsole allows you interact with slap API. You can play with the global
    "slap" object and with the global "request" method.

    examples :
    >>> # Request instance
    >>> request(kvm, "myuniquekvm")
    >>> # Request software installation on owned computer
    >>> supply(kvm, "mycomputer")
    >>> # Fetch instance informations on already launched instance
    >>> request(kvm, "myuniquekvm").getConnectionParameter("url")
    """
    # XXX TODO: docstring is printed without newlines

    log = logging.getLogger(__name__)

    def take_action(self, args):
        configuration_parser = self.fetch_config(args)
        config = ClientConfig(args, configuration_parser)
        local = init(config)
        do_console(local)

