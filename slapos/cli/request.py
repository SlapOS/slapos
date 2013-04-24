# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, do_request, ClientConfig


def parse_option_dict(options):
    """
    Parse a list of option strings like foo=bar baz=qux and return a dictionary.
    Will raise if keys are repeated.
    """
    ret = {}
    for option_pair in (options or []):
        key, value = option_pair.split('=', 1)
        if key in ret:
            raise ValueError("Multiple values provided for the same key '%s'" % key)
        ret[key] = value
    return ret


class RequestCommand(ClientConfigCommand):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        ap = super(RequestCommand, self).get_parser(prog_name)

        ap.add_argument('reference',
                        help='Your instance reference')

        ap.add_argument('software_url',
                        help='Your software url')

        ap.add_argument('--node',
                        nargs='+',
                        help="Node request option 'option1=value1 option2=value2'")

        ap.add_argument('--type',
                        help='Define software type to be requested')

        ap.add_argument('--slave',
                        action='store_true',
                        help='Ask for a slave instance')

        # XXX maybe find a better name? we already have a global --cfg option
        ap.add_argument('--configuration',
                        nargs='+',
                        help="Give your configuration 'option1=value1 option2=value2'")

        return ap

    def take_action(self, args):
        args.node = parse_option_dict(args.node)
        args.configuration = parse_option_dict(args.configuration)

        configuration_parser = self.fetch_config(args)
        config = ClientConfig(args, configuration_parser)

        local = init(config)
        do_request(config, local)
