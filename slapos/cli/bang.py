# -*- coding: utf-8 -*-

from slapos.cli.command import must_be_root
from slapos.cli.config import ConfigCommand
from slapos.bang import do_bang


class BangCommand(ConfigCommand):
    """
    request update on all partitions
    """
    command_group = 'node'

    def get_parser(self, prog_name):
        ap = super(BangCommand, self).get_parser(prog_name)
        ap.add_argument('-m', '--message',
                        help='Message for bang')
        return ap

    @must_be_root
    def take_action(self, args):
        configp = self.fetch_config(args)
        do_bang(configp, args.message)
