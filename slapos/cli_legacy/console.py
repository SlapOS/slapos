# -*- coding: utf-8 -*-

import argparse
import os
import textwrap

from slapos.client import ClientConfig, init, do_console
from slapos.cli_legacy.util import get_config_parser


def console():
  description = textwrap.dedent("""\
    slapconsole allows you interact with slap API. You can play with the global
    "slap" object and with the global "request" method.

    examples :
    >>> # Request instance
    >>> request(kvm, "myuniquekvm")
    >>> # Request software installation on owned computer
    >>> supply(kvm, "mycomputer")
    >>> # Fetch instance informations on already launched instance
    >>> request(kvm, "myuniquekvm").getConnectionParameter("url")""")

  ap = argparse.ArgumentParser(description=description,
                               formatter_class=argparse.RawDescriptionHelpFormatter)

  ap.add_argument('-u', '--master_url',
                  default=None,
                  help='Url of SlapOS Master to use.')

  ap.add_argument('-k', '--key_file',
                  help="SSL Authorisation key file.")

  ap.add_argument('-c', '--cert_file',
                  help="SSL Authorisation certificate file.")

  ap.add_argument('configuration_file',
                  help='path to slapos.cfg')

  args = ap.parse_args()

  if not os.path.isfile(args.configuration_file):
    ap.error("%s: Not found or not a regular file." % args.configuration_file)

  configp = get_config_parser(args.configuration_file)
  conf = ClientConfig(args, configp)
  local = init(conf)
  do_console(local)
