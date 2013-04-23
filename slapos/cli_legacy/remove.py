# -*- coding: utf-8 -*-

import argparse

from slapos.client import ClientConfig, init, do_remove
from slapos.cli_legacy.util import get_config_parser


def remove():
  """
  Run when invoking slapos remove. Mostly argument parsing.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('configuration_file',
                      help='SlapOS configuration file')
  parser.add_argument('software_url',
                      help='Your software url')
  parser.add_argument('node',
                      help='Target node')
  args = parser.parse_args()

  config = ClientConfig(args, get_config_parser(args.configuration_file))
  local = init(config)
  do_remove(args.software_url, args.node, local)
