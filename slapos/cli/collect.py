# -*- coding: utf-8 -*-

import subprocess
from time import sleep
import socket
import glob
import os
from slapos.collect import do_collect
from slapos.cli.command import must_be_root
from slapos.cli.entry import SlapOSApp
from slapos.cli.config import ConfigCommand

class CollectCommand(ConfigCommand):
    """
    Collect system consumption and data and store.
    """
    command_group = 'node'

    def get_parser(self, prog_name):
        ap = super(CollectCommand, self).get_parser(prog_name)
        return ap

    @must_be_root
    def take_action(self, args):
        configp = self.fetch_config(args)
        do_collect(configp)
