# -*- coding: utf-8 -*-
# vim: set et sts=2:

import argparse
import ConfigParser
import logging
import sys

from slapos.grid.utils import setRunning, setFinished
from slapos.grid.slapgrid import (merged_options, check_missing_parameters,
                                  check_missing_files, random_delay, create_slapgrid_object)


def parse_arguments(*argument_tuple):
  """Parse arguments and return options dictionary merged with the config file."""

  ap = argparse.ArgumentParser()
  ap.add_argument('--instance-root',
                  help='The instance root directory location.')
  ap.add_argument('--software-root',
                  help='The software_root directory location.')
  ap.add_argument('--master-url',
                  help='The master server URL. Mandatory.')
  ap.add_argument('--computer-id',
                  help='The computer id defined in the server.')
  ap.add_argument('--supervisord-socket',
                  help='The socket supervisor will use.')
  ap.add_argument('--supervisord-configuration-path',
                  help='The location where supervisord configuration will be stored.')
  ap.add_argument('--buildout', default=None,
                  help='Location of buildout binary.')
  ap.add_argument('--pidfile',
                  help='The location where pidfile will be created.')
  ap.add_argument('--logfile',
                  help='The location where slapgrid logfile will be created.')
  ap.add_argument('--key_file',
                  help='SSL Authorisation key file.')
  ap.add_argument('--cert_file',
                  help='SSL Authorisation certificate file.')
  ap.add_argument('--signature_private_key_file',
                  help='Signature private key file.')
  ap.add_argument('--master_ca_file',
                  help='Root certificate of SlapOS master key.')
  ap.add_argument('--certificate_repository_path',
                  help='Path to directory where downloaded certificates would be stored.')
  ap.add_argument('-v', '--verbose', action='store_true',
                  help='Be verbose.')
  ap.add_argument('--maximum-periodicity', type=int, default=None,
                  help='Periodicity at which buildout should be run in instance.')
  ap.add_argument('--promise-timeout', type=int, default=3,
                  help='Promise timeout in seconds.')
  ap.add_argument('--now', action='store_true',
                  help='Launch slapgrid without delay. Default behavior.')
  ap.add_argument('--all', action='store_true',
                  help='Launch slapgrid to process all Softare Releases '
                       'and/or Computer Partitions.')
  ap.add_argument('--only-sr',
                  help='Force the update of a single software release (use url hash), '
                       'even if is already installed. This option will make all others '
                       'sofware releases be ignored.')
  ap.add_argument('--only-cp',
                  help='Update a single or a list of computer partitions '
                       '(ie.:slappartX, slappartY), '
                       'this option will make all others computer partitions be ignored.')

  ap.add_argument('configuration_file', type=argparse.FileType(),
                  help='SlapOS configuration file.')

  # Deprecated options
  ap.add_argument('-c', '--console', action='store_true',
                  help="Deprecated, doesn't do anything.")
  ap.add_argument('--develop', action='store_true',
                  help='Deprecated, same as --all.')
  ap.add_argument('--only_sr',
                  help='Deprecated, same as --only-sr.')
  ap.add_argument('--only_cp',
                  help='Deprecated, same as --only-cp.')
  ap.add_argument('--maximal_delay',
                  help='Deprecated. Will only work from configuration file in the future.')

  if not argument_tuple:
    args = ap.parse_args()
  else:
    args = ap.parse_args(list(argument_tuple))

  return args


def setup_logger(options):
  logger = logging.getLogger(__name__)

  if options.get('logfile'):
    handler = logging.FileHandler(options['logfile'])
  else:
    handler = logging.StreamHandler()

  if options['verbose']:
    handler.setLevel(logging.DEBUG)
  else:
    handler.setLevel(logging.INFO)

  formatter = logging.Formatter(fmt='%(asctime)s %(name)-18s: '
                                '%(levelname)-8s %(message)s',
                                datefmt='%Y-%m-%dT%H:%M:%S')

  handler.setFormatter(formatter)
  logger.addHandler(handler)

  return logger


def parseArgumentTupleAndReturnSlapgridObject(*argument_tuple):
  """Returns a new instance of slapgrid.Slapgrid created with argument+config parameters.
     Also returns the pidfile path, and configures logger.
  """
  args = parse_arguments(*argument_tuple)

  configp = ConfigParser.SafeConfigParser()
  configp.readfp(args.configuration_file)

  options = merged_options(args, configp)

  logger = setup_logger(options)

  check_missing_parameters(options)
  check_missing_files(options)

  random_delay(options, logger=logger)

  slapgrid_object = create_slapgrid_object(options, logger=logger)

  return slapgrid_object, options.get('pidfile')


def realRun(argument_tuple, method):
  slapgrid_object, pidfile = parseArgumentTupleAndReturnSlapgridObject(*argument_tuple)
  if pidfile:
    setRunning(logger=slapgrid_object.logger, pidfile=pidfile)
  try:
    return getattr(slapgrid_object, method)()
  finally:
    if pidfile:
      setFinished(pidfile)


def runSoftwareRelease(*argument_tuple):
  """Hook for entry point to process Software Releases"""
  sys.exit(realRun(argument_tuple, 'processSoftwareReleaseList'))


def runComputerPartition(*argument_tuple):
  """Hook for entry point to process Computer Partitions"""
  sys.exit(realRun(argument_tuple, 'processComputerPartitionList'))


def runUsageReport(*argument_tuple):
  """Hook for entry point to process Usage Reports"""
  sys.exit(realRun(argument_tuple, 'agregateAndSendUsage'))
