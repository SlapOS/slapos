# -*- coding: utf-8 -*-

import logging
import sys

from slapos.cli.command import must_be_root
from slapos.cli.config import ConfigCommand
from slapos.format import do_format, FormatConfig, tracing_monkeypatch, UsageError


class FormatCommand(ConfigCommand):
    """
    create users, partitions and network configuration
    """

    log = logging.getLogger('format')

    def get_parser(self, prog_name):
        ap = super(FormatCommand, self).get_parser(prog_name)

        ap.add_argument('-x', '--computer_xml',
                        help="Path to file with computer's XML. If does not exists, will be created",
                        default=None)

        ap.add_argument('--computer_json',
                        help="Path to a JSON version of the computer's XML (for development only).",
                        default=None)

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

    @must_be_root
    def take_action(self, args):
        configp = self.fetch_config(args)

        conf = FormatConfig(logger=self.log)

        conf.mergeConfig(args, configp)

        if not self.app.options.log_file and conf.log_file:
            # no log file is provided by argparser,
            # we set up the one from config
            file_handler = logging.FileHandler(conf.log_file)
            formatter = logging.Formatter(self.app.LOG_FILE_MESSAGE_FORMAT)
            file_handler.setFormatter(formatter)
            self.log.addHandler(file_handler)

        try:
            conf.setConfig()
        except UsageError as err:
            sys.stderr.write(err.message + '\n')
            sys.stderr.write("For help use --help\n")
            sys.exit(1)

        tracing_monkeypatch(conf)

        try:
            do_format(conf=conf)
        except:
            self.log.exception('Uncaught exception:')
            raise
