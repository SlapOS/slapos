# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import logging
import sys

from slapos.cli.command import check_root_user
from slapos.cli.config import ConfigCommand
from slapos.format import do_format, FormatConfig, tracing_monkeypatch, UsageError
from slapos.util import string_to_boolean

class FormatCommand(ConfigCommand):
    """
    create users, partitions and network configuration
    """
    command_group = 'node'

    def get_parser(self, prog_name):
        ap = super(FormatCommand, self).get_parser(prog_name)

        ap.add_argument('-x', '--computer_xml',
                        help="Path to file with computer's XML. If does not exists, will be created")

        ap.add_argument('--computer_json',
                        help="Path to a JSON version of the computer's XML (for development only)")

        ap.add_argument('-i', '--input_definition_file',
                        help="Path to file to read definition of computer instead of "
                        "declaration. Using definition file allows to disable "
                        "'discovery' of machine services and allows to define computer "
                        "configuration in fully controlled manner.")

        ap.add_argument('-o', '--output_definition_file',
                        help="Path to file to write definition of computer from "
                        "declaration.")

        ap.add_argument('--alter_user',
                        choices=['True', 'False'],
                        help='Shall slapformat alter user database'
                             ' (default: %(default)s)')

        ap.add_argument('--alter_network',
                        choices=['True', 'False'],
                        help='Shall slapformat alter network configuration'
                             ' (default: %(default)s)')

        ap.add_argument('--now',
                        default=False,
                        action="store_true",
                        help='Launch slapformat without delay'
                             ' (default: %(default)s)')

        ap.add_argument('-n', '--dry_run',
                        default=False,
                        action="store_true",
                        help="Don't actually do anything"
                             " (default: %(default)s)")

        ap.add_argument('-c', '--console',
                        help="Console output (obsolete)")
        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)

        conf = FormatConfig(logger=self.app.log)

        conf.mergeConfig(args, configp)

        # Parse if we have to check if running from root
        # XXX document this feature.
        if string_to_boolean(getattr(conf, 'root_check', 'True').lower()):
          check_root_user(self)

        if len(self.app.log.handlers) == 0 and not self.app.options.log_file and conf.log_file:
            # This block is called again if "slapos node boot" failed.
            # Don't add a handler again, otherwise the output becomes double.
            #
            # no log file is provided by argparser,
            # we set up the one from config
            file_handler = logging.FileHandler(conf.log_file)
            formatter = logging.Formatter(self.app.LOG_FILE_MESSAGE_FORMAT)
            file_handler.setFormatter(formatter)
            self.app.log.addHandler(file_handler)

        try:
            conf.setConfig()
        except UsageError as err:
            sys.stderr.write(err.message + '\n')
            sys.stderr.write("For help use --help\n")
            sys.exit(1)

        tracing_monkeypatch(conf)

        do_format(conf=conf)
