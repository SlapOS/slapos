# -*- coding: utf-8 -*-

import argparse

from slapos.client import ClientConfig, init, do_remove
from slapos.cli_legacy.util import get_config_parser


def remove():
  ap = argparse.ArgumentParser()
  ap.add_argument('configuration_file',
                  help='SlapOS configuration file')
  ap.add_argument('software_url',
                  help='Your software url')
  ap.add_argument('node',
                  help='Target node')
  args = ap.parse_args()

  configp = get_config_parser(args.configuration_file)
  conf = ClientConfig(args, configp)
  local = init(conf)
  do_remove(args.software_url, args.node, local)
