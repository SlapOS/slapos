# -*- coding: utf-8 -*-

import argparse
import functools
import os
import sys

from cliff import command


class Command(command.Command):

    def get_parser(self, prog_name):
        parser = argparse.ArgumentParser(
            description=self.get_description(),
            prog=prog_name,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        return parser

def check_root_user(config_command_instance):
  if sys.platform != 'cygwin' and os.getuid() != 0:
      config_command_instance.app.log.error('This slapos command must be run as root.')
      sys.exit(5)

def must_be_root(func):
    @functools.wraps(func)
    def inner(self, *args, **kw):
        check_root_user(self)
        return func(self, *args, **kw)
    return inner
