# -*- coding: utf-8 -*-

import logging
import sys

from slapos.cli.config import ConfigCommand
from slapos.format import do_format, FormatConfig, tracing_monkeypatch, UsageError


class FormatCommand(ConfigCommand):

    log = logging.getLogger('slapformat')

    def get_parser(self, prog_name):
        ap = super(FormatCommand, self).get_parser(prog_name)

        ap.add_argument('-x', '--computer_xml',
                        help="Path to file with computer's XML. If does not exists, will be created",
                        default=None)

        ap.add_argument('--computer_json',
                        help="Path to a JSON version of the computer's XML (for development only).",
                        default=None)

        ap.add_argument('-l', '--log_file',
                        help="The path to the log file used by the script.")

        ap.add_argument('-i', '--input_definition_file',
                        help="Path to file to read definition of computer instead of "
                        "declaration. Using definition file allows to disable "
                        "'discovery' of machine services and allows to define computer "
                        "configuration in fully controlled manner.")

        ap.add_argument('-o', '--output_definition_file',
                        help="Path to file to write definition of computer from "
                        "declaration.")

        ap.add_argument('-n', '--dry_run',
                        help="Don't actually do anything.",
                        default=False,
                        action="store_true")

        ap.add_argument('--alter_user',
                        choices=['True', 'False'],
                        help="Shall slapformat alter user database [default: True]")

        ap.add_argument('--alter_network',
                        choices=['True', 'False'],
                        help="Shall slapformat alter network configuration [default: True]")

        ap.add_argument('--now',
                        help="Launch slapformat without delay",
                        default=False,
                        action="store_true")

        return ap

    def take_action(self, args):
        configuration_parser = self.fetch_config(args)

        config = FormatConfig(logger=self.log)

        try:
            config.setConfig(args, configuration_parser)
        except UsageError as err:
            sys.stderr.write(err.message + '\n')
            sys.stderr.write("For help use --help\n")
            sys.exit(1)

        tracing_monkeypatch(config)

        try:
            do_format(config=config)
        except:
            self.log.exception('Uncaught exception:')
            raise
