# -*- coding: utf-8 -*-

import argparse

import cliff


class Command(cliff.command.Command):
    def get_parser(self, prog_name):
        parser = argparse.ArgumentParser(
            description=self.get_description(),
            prog=prog_name,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        return parser
