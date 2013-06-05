# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ConfigCommand
from slapos.cache import do_lookup


class CacheLookupCommand(ConfigCommand):
    """
    perform a query to the networkcache
    You can provide either a complete URL to the software release,
    or a corresponding MD5 hash value.

    The command will report which OS distribution/version have a binary
    cache of the software release, and which ones are compatible
    with the OS you are currently running.
    """

    log = logging.getLogger('cache-lookup')

    def get_parser(self, prog_name):
        ap = super(CacheLookupCommand, self).get_parser(prog_name)
        ap.add_argument('software_url',
                        help='Your software url or MD5 hash')
        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        do_lookup(configp, args.software_url, logger=self.app.log)
