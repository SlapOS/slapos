# -*- coding: utf-8 -*-

import textwrap

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, do_console, ClientConfig


class ShellNotFound(Exception):
    pass


class ConsoleCommand(ClientConfigCommand):
    """
    open python console with slap library imported

    You can play with the global "slap" object and
    with the global "request" method.

    examples :
    >>> # Request instance
    >>> request(kvm, "myuniquekvm")
    >>> # Request software installation on owned computer
    >>> supply(kvm, "mycomputer")
    >>> # Fetch instance informations on already launched instance
    >>> request(kvm, "myuniquekvm").getConnectionParameter("url")
    """

    def get_parser(self, prog_name):
        ap = super(ConsoleCommand, self).get_parser(prog_name)

        ap.add_argument('-u', '--master_url',
                        help='Url of SlapOS Master to use')

        ap.add_argument('-k', '--key_file',
                        help='SSL Authorisation key file')

        ap.add_argument('-c', '--cert_file',
                        help='SSL Authorisation certificate file')

        shell = ap.add_mutually_exclusive_group()

        shell.add_argument('-i', '--ipython',
                           action='store_true',
                           help='Use IPython shell if available (default)')

        shell.add_argument('-b', '--bpython',
                           action='store_true',
                           help='Use BPython shell if available')

        shell.add_argument('-p', '--python',
                           action='store_true',
                           help='Use plain Python shell')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)
        local = init(conf, self.app.log)

        if not any([args.python, args.ipython, args.bpython]):
            args.ipython = True

        if args.ipython:
            try:
                do_ipython_console(local)
            except ShellNotFound:
                self.app.log.info('IPython not available - using plain Python shell')
                do_console(local)
        elif args.bpython:
            try:
                do_bpython_console(local)
            except ShellNotFound:
                self.app.log.info('bpython not available - using plain Python shell')
                do_console(local)
        else:
            do_console(local)


console_banner = """\
slapos console allows you interact with slap API. You can play with the global
"slap" object and with the global request() and supply() methods.

examples :
>>> # Request instance
>>> request(kvm, "myuniquekvm")
>>> # Request software installation on owned computer
>>> supply(kvm, "mycomputer")
>>> # Fetch instance informations on already launched instance
>>> request(kvm, "myuniquekvm").getConnectionParameter("url")
"""


def do_bpython_console(local):
    try:
        from bpython import embed
    except ImportError:
        raise ShellNotFound
    embed(banner=console_banner,
          locals_=local)


def do_ipython_console(local):
    try:
        from IPython import embed
    except ImportError:
        raise ShellNotFound
    embed(banner1=console_banner,
          user_ns=local)
