# -*- coding: utf-8 -*-

import argparse

from slapos.client import ClientConfig, init, do_request
from slapos.cli_legacy.util import get_config_parser


def argToDict(element):
  """
  convert a table of string 'key=value' to dict
  """
  if element is not None:
    element_dict = dict([arg.split('=') for arg in element])
  return element_dict


def request():
  """Run when invoking slapos request. Request an instance."""
  # Parse arguments and inititate needed parameters
  # XXX-Cedric: move argument parsing to main entry point

  ap = argparse.ArgumentParser()
  ap.add_argument('configuration_file',
                  help='SlapOS configuration file.')
  ap.add_argument('reference',
                  help='Your instance reference')
  ap.add_argument('software_url',
                  help='Your software url')
  ap.add_argument('--node',
                  nargs='*',
                  help='Node request option '
                  "'option1=value1 option2=value2'")
  ap.add_argument('--type',
                  type=str,
                  help='Define software type to be requested')
  ap.add_argument('--slave',
                  action='store_true', default=False,
                  help='Ask for a slave instance')
  ap.add_argument('--configuration',
                  nargs='*',
                  help='Give your configuration '
                  "'option1=value1 option2=value2'")

  args = ap.parse_args()

  if args.configuration:
    args.configuration = argToDict(args.configuration)

  if args.node:
    args.node = argToDict(args.node)

  configp = get_config_parser(args.configuration_file)
  conf = ClientConfig(args, configp)
  local = init(conf)
  do_request(conf, local)
