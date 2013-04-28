# -*- coding: utf-8 -*-

import argparse

from slapos.client import ClientConfig, init, do_supply
from slapos.cli_legacy.util import get_config_parser


def supply():
  """
  Run when invoking slapos supply. Mostly argument parsing.
  """
  ap = argparse.ArgumentParser()
  ap.add_argument('configuration_file',
                  help='SlapOS configuration file')
  ap.add_argument('software_url',
                  help='Your software url')
  ap.add_argument('node',
                  help='Target node')
  args = ap.parse_args()

  config = ClientConfig(args, get_config_parser(args.configuration_file))
  local = init(config)
  do_supply(args.software_url, args.node, local)
