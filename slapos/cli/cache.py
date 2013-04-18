# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ConfigCommand
from slapos.cache import do_lookup


class CacheLookupCommand(ConfigCommand):

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(CacheLookupCommand, self).get_parser(prog_name)
        # XXX this argument could use a better name
        parser.add_argument('software_url',
                            help='Your software url or MD5 hash')
        return parser

    def take_action(self, args):
        config = self.fetch_config(args)
        do_lookup(config, args.software_url)
