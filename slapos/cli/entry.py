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

import argparse
import codecs
import collections
import locale
import logging
import sys

import os
# hack to avoid a bug in cmd2: https://bitbucket.org/catherinedevlin/cmd2/issue/1/silent-editor-check
# must be done before importing cliff
os.environ.setdefault('EDITOR', 'vi')

from cliff.app import App
from cliff.commandmanager import CommandManager, LOG
from requests.packages import urllib3

import slapos.version

# silence messages like 'Starting connection' that are logged with INFO
urllib3_logger = logging.getLogger('requests.packages.urllib3')
urllib3_logger.setLevel(logging.WARNING)
urllib3.disable_warnings()


class SlapOSCommandManager(CommandManager):

    def find_command(self, argv):
        """Given an argument list, find a command and
        return the processor and any remaining arguments.
        """
        # a little cheating, 'slapos node' is not documented by the help command
        if argv == ['node']:
            argv = ['node', 'status']

        search_args = argv[:]
        name = ''
        while search_args:
            if search_args[0].startswith('-'):
                LOG.critical('slapos: invalid option %r' % search_args[0])
                sys.exit(5)
            next_val = search_args.pop(0)
            name = '%s %s' % (name, next_val) if name else next_val
            if name in self.commands:
                cmd_ep = self.commands[name]
                cmd_factory = cmd_ep.load()
                return (cmd_factory, name, search_args)
        else:
            LOG.critical('slapos: the command %r does not exist or is not yet implemented.\n'
                         '\n'
                         'Available commands: %s\n\n'
                         'Please find documentation and forum at http://community.slapos.org\n'
                         'Please also make sure that the SlapOS Node package is up to date.',
                         ' '.join(argv),
                         ', '.join(sorted(repr(c) for c in self.commands)))
            sys.exit(5)


class SlapOSHelpAction(argparse.Action):
    """
    Adapted from cliff.help.HelpAction, this class detects
    and outputs command groups, via the .command_group attribute
    of the Command class. Must be a class attribute in case the class
    cannot be instantiated ('Could not load' message).
    """
    def __call__(self, parser, namespace, values, option_string=None):
        app = self.default
        parser.print_help(app.stdout)
        command_manager = app.command_manager
        groups = collections.defaultdict(list)
        for name, ep in sorted(command_manager):
            command_group, help_line = self._help_line(ep, name)
            groups[command_group].append(help_line)

        for group in sorted(groups):
            app.stdout.write('\n%s commands:\n' % group)
            for line in sorted(groups[group]):
                app.stdout.write(line)
        sys.exit(0)

    def _help_line(self, ep, name):
        try:
            factory = ep.load()
        except Exception as err:
            return 'Could not load %r\n' % ep
        try:
            cmd = factory(self, None)
        except Exception as err:
            return 'Could not instantiate %r: %s\n' % (ep, err)
        one_liner = cmd.get_description().split('\n')[0]
        group = getattr(factory, 'command_group', 'other')
        return group, '  %-13s  %s\n' % (name, one_liner)


class SlapOSApp(App):

    #
    # self.options.verbose_level:
    #    -q  -> 0 (WARNING)
    #        -> 1 (INFO)
    #    -v  -> 2 (DEBUG)
    #    -vv -> 3 (...)
    #    etc.
    #

    log = logging.getLogger('slapos')

    def __init__(self):
        super(SlapOSApp, self).__init__(
            description='SlapOS client %s' % slapos.version.version,
            version=slapos.version.version,
            command_manager=SlapOSCommandManager('slapos.cli'),
        )

    def _set_streams(self, stdin, stdout, stderr):
        try:
            # SlapOS: might fail in some systems
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error:
            pass

        if sys.version_info[:2] == (2, 6):
            # Configure the input and output streams. If a stream is
            # provided, it must be configured correctly by the
            # caller. If not, make sure the versions of the standard
            # streams used by default are wrapped with encodings. This
            # works around a problem with Python 2.6 fixed in 2.7 and
            # later (http://hg.python.org/cpython/rev/e60ef17561dc/).
            lang, encoding = locale.getdefaultlocale()
            encoding = getattr(sys.stdout, 'encoding', None) or encoding
            self.stdin = stdin or codecs.getreader(encoding)(sys.stdin)
            self.stdout = stdout or codecs.getwriter(encoding)(sys.stdout)
            self.stderr = stderr or codecs.getwriter(encoding)(sys.stderr)
        else:
            self.stdin = stdin or sys.stdin
            self.stdout = stdout or sys.stdout
            self.stderr = stderr or sys.stderr

    def build_option_parser(self, *args, **kw):
        kw.setdefault('argparse_kwargs', {})
        kw['argparse_kwargs']['conflict_handler'] = 'resolve'
        parser = super(SlapOSApp, self).build_option_parser(*args, **kw)

        # add two aliases for --log-file (for compatibility with old commands)
        parser.add_argument(
            '--log-file', '--logfile', '--log_file',
            action='store',
            default=None,
            help='Specify a file to log output (default: console only)',
        )
        parser.add_argument(
            '--log-color',
            action='store_true',
            help='Colored log output in console (stripped if redirected)',
            default=True,
        )
        parser.add_argument(
            '--log-time',
            action='store_false',
            default=True,
            help='Include timestamp in console log',
        )
        parser.add_argument(
            '-h', '--help',
            action=SlapOSHelpAction,
            nargs=0,
            default=self,  # tricky
            help="show this help message and exit",
        )
        return parser

    def initialize_app(self, argv):
        if self.options.verbose_level > 2:
            self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        if self.options.verbose_level > 2:
            self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        if self.options.verbose_level > 2:
            self.log.debug('clean_up %s', cmd.__class__.__name__)

    @property
    def CONSOLE_MESSAGE_FORMAT(self):
        fmt = []
        if self.options.log_time and not self.options.log_color:
            fmt.append('[%(asctime)s]')
        if not self.options.log_color:
            fmt.append('%(levelname)s')
        fmt.append('%(message)s')
        return ' '.join(fmt)

    @property
    def LOG_FILE_MESSAGE_FORMAT(self):
        return '[%(asctime)s] %(levelname)-8s %(message)s'

    def configure_logging(self):
        """Create logging handlers for any log output.
        """
        root_logger = logging.getLogger('')
        root_logger.setLevel(logging.DEBUG)

        # Set up logging to a file
        if self.options.log_file:
            file_handler = logging.FileHandler(
                filename=self.options.log_file,
            )
            formatter = logging.Formatter(self.LOG_FILE_MESSAGE_FORMAT)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Always send higher-level messages to the console via stderr

        # This function is called again if "slapos node boot" failed.
        # Don't add a handler again, otherwise the output becomes double.
        if [handler for handler in root_logger.handlers
            if isinstance(handler, logging.StreamHandler)]:
          return

        if self.options.log_color:
            import coloredlogs
            console = coloredlogs.ColoredStreamHandler(show_name=True,     # logger name (slapos) and PID
                                                       show_severity=True,
                                                       show_timestamps=self.options.log_time,
                                                       show_hostname=False)
        else:
            console = logging.StreamHandler(self.stderr)
        console_level = {0: logging.WARNING,
                         1: logging.INFO,
                         2: logging.DEBUG,
                         }.get(self.options.verbose_level, logging.DEBUG)
        console.setLevel(console_level)
        formatter = logging.Formatter(self.CONSOLE_MESSAGE_FORMAT)
        console.setFormatter(formatter)
        root_logger.addHandler(console)
        return

    def run(self, argv):
        # same as cliff.app.App.run except that it won't re-raise
        # a logged exception, and doesn't use --debug
        self.options, remainder = self.parser.parse_known_args(argv)
        self.configure_logging()
        self.interactive_mode = not remainder
        try:
            self.initialize_app(remainder)
        except Exception as err:
            self.log.exception(err)
            return 1
        if self.interactive_mode:
            result = self.interact()
        else:
            result = self.run_subcommand(remainder)
        return result

    def run_subcommand(self, argv):
        # same as cliff.app.App.run_subcommand except that it won't re-raise
        # a logged exception, and doesn't use --debug
        subcommand = self.command_manager.find_command(argv)
        cmd_factory, cmd_name, sub_argv = subcommand
        cmd = cmd_factory(self, self.options)
        err = None
        result = 1
        try:
            self.prepare_to_run_command(cmd)
            full_name = (cmd_name
                         if self.interactive_mode
                         else ' '.join([self.NAME, cmd_name])
                         )
            cmd_parser = cmd.get_parser(full_name)
            parsed_args = cmd_parser.parse_args(sub_argv)
            result = cmd.run(parsed_args)
        except Exception as err:
            self.log.exception(err)
            try:
                self.clean_up(cmd, result, err)
            except Exception as err2:
                self.log.exception(err2)
        else:
            try:
                self.clean_up(cmd, result, None)
            except Exception as err3:
                self.log.exception(err3)
        return result


def main(argv=sys.argv[1:]):
    app = SlapOSApp()
    if not argv:
        argv = ['-h']
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
