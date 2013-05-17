# -*- coding: utf-8 -*-

import argparse
import functools
import os
import sys

import cliff


class Command(cliff.command.Command):

    def get_parser(self, prog_name):
        parser = argparse.ArgumentParser(
            description=self.get_description(),
            prog=prog_name,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        return parser


def must_be_root(func):
    @functools.wraps(func)
    def func(self, *args, **kw):
        if os.getuid() != 0:
            self.app.log.error('This slapos command must be run as root.')
            sys.exit(5)
    return func
