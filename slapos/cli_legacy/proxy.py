# -*- coding: utf-8 -*-
# vim: set et sts=2:

import argparse
import ConfigParser
import logging
import os
import sys

from slapos.proxy import ProxyConfig, do_proxy

class UsageError(Exception):
  pass


def main():
  ap = argparse.ArgumentParser()

  ap.add_argument('-l', '--log_file',
                  help='The path to the log file used by the script.')

  ap.add_argument('-v', '--verbose',
                  action='store_true',
                  help='Verbose output.')

  # XXX not used anymore, deprecated
  ap.add_argument('-c', '--console',
                  action='store_true',
                  help='Console output.')

  ap.add_argument('-u', '--database-uri',
                  help='URI for sqlite database')

  ap.add_argument('configuration_file',
                  help='path to slapos.cfg')

  args = ap.parse_args()

  logger = logging.getLogger('slapproxy')
  logger.addHandler(logging.StreamHandler())

  if args.verbose:
    logger.setLevel(logging.DEBUG)
  else: 
    logger.setLevel(logging.INFO)

  conf = ProxyConfig(logger)

  configp = ConfigParser.SafeConfigParser()
  if configp.read(args.configuration_file) != [args.configuration_file]:
    raise UsageError('Cannot find or parse configuration file: %s' % args.configuration_file)

  conf.mergeConfig(args, configp)

  if conf.log_file:
    if not os.path.isdir(os.path.dirname(conf.log_file)):
      raise ValueError('Please create directory %r to store %r log file' % (
        os.path.dirname(conf.log_file), conf.log_file))
    file_handler = logging.FileHandler(conf.log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    logger.info('Configured logging to file %r' % conf.log_file)

  conf.setConfig()

  try:
    do_proxy(conf=conf)
    return_code = 0
  except SystemExit as err:
    return_code = err

  sys.exit(return_code)
