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
    """request an instance and get status and parameters of instance"""

    log = logging.getLogger('request')

    def get_parser(self, prog_name):
        ap = super(RequestCommand, self).get_parser(prog_name)

        ap.add_argument('reference',
                        help='Your instance reference')

        ap.add_argument('software_url',
                        help='Your software url')
        # XXX TODO can this be an MD5 hash?
        # XXX TODO can we do a minimal check for correctness of this argument?
        #          the alternative is a silent failure for mistyped/obsolete/invalid URL

        ap.add_argument('--node',
                        nargs='+',
                        help="Node request option 'option1=value1 option2=value2'")

        ap.add_argument('--type',
                        help='Software type to be requested')

        ap.add_argument('--state',
                        help='State of the requested instance')

        ap.add_argument('--slave',
                        action='store_true',
                        help='Ask for a slave instance')

        ap.add_argument('--parameters',
                        nargs='+',
                        help="Give your configuration 'option1=value1 option2=value2'")

        return ap

    def take_action(self, args):
        args.node = parse_option_dict(args.node)
        args.parameters = parse_option_dict(args.parameters)

        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)

        local = init(conf)
        do_request(conf, local)
