# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import argparse
import ConfigParser
import logging
import os
import pkg_resources
import random
import socket
import StringIO
import subprocess
import sys
import tempfile
import time
import traceback
import warnings

if sys.version_info < (2, 6):
  warnings.warn('Used python version (%s) is old and has problems with'
      ' IPv6 connections' % sys.version.split('\n')[0])

from lxml import etree

from slapos.slap.slap import NotFoundError
from slapos.slap.slap import ServerError
from slapos.grid.exception import BuildoutFailedError
from slapos.grid.SlapObject import Software, Partition
from slapos.grid.svcbackend import launchSupervisord
from slapos.grid.utils import (md5digest, createPrivateDirectory, dropPrivileges,
                               setRunning, setFinished, SlapPopen, updateFile)
import slapos.slap


# XXX: should be moved to SLAP library
COMPUTER_PARTITION_DESTROYED_STATE = 'destroyed'
COMPUTER_PARTITION_STARTED_STATE = 'started'
COMPUTER_PARTITION_STOPPED_STATE = 'stopped'

# Global variables about return state of slapgrid
SLAPGRID_SUCCESS = 0
SLAPGRID_FAIL = 1
SLAPGRID_PROMISE_FAIL = 2

# XXX hardcoded watchdog_path
WATCHDOG_PATH = '/opt/slapos/bin/slapos-watchdog'

COMPUTER_PARTITION_TIMESTAMP_FILENAME = '.timestamp'


class _formatXMLError(Exception):
  pass


def check_missing_parameters(options):
  required = set([
      'computer_id',
      'instance_root',
      'master_url',
      'software_root',
  ])

  if 'key_file' in options:
    required.add('certificate_repository_path')
    required.add('cert_file')
  if 'cert_file' in options:
    required.add('certificate_repository_path')
    required.add('key_file')

  missing = required.difference(options)

  if missing:
    raise RuntimeError('Missing mandatory parameters: %s' % ', '.join(sorted(missing)))


def check_missing_files(options):
  req_files = [
          options.get('key_file'),
          options.get('cert_file'),
          options.get('master_ca_file'),
          options.get('shacache-cert-file'),
          options.get('shacache-key-file'),
          options.get('shadir-cert-file'),
          options.get('shadir-key-file'),
          options.get('signature_private_key_file')
          ]

  req_dirs = [
          options.get('certificate_repository_path')
          ]

  for f in req_files:
    if f and not os.path.exists(f):
        raise RuntimeError('File %r does not exist.' % f)

  for d in req_dirs:
    if d and not os.path.isdir(d):
      raise RuntimeError('Directory %r does not exist' % d)


def parse_arguments_merge_config(*argument_tuple):
  """Parse arguments and return options dictionary
     merged with the config file."""

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
  ap.add_argument("--only-cp",
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

  options = {}
  config = ConfigParser.SafeConfigParser()
  config.readfp(args.configuration_file)

  options = dict(config.items('slapos'))
  if config.has_section('networkcache'):
    options.update(dict(config.items('networkcache')))
  for key, value in vars(args).iteritems():
    if value is not None:
      options[key] = value

  return options


def setup_logger(options):
  # Configures logger.
  if options['verbose']:
    level = logging.DEBUG
  else:
    level = logging.INFO
  logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                      level=level,
                      datefmt='%Y-%m-%dT%H:%M:%S')
  if options.get('logfile'):
    console = logging.FileHandler(options['logfile'])
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        '%(asctime)s %(name)-18s: %(levelname)-8s %(message)s'))
    logging.getLogger('').addHandler(console)

  # XXX return and use logger object



def random_delay(options):
  """
  Sleep for a random time to avoid SlapOS Master being DDOSed by an army of
  SlapOS Nodes configured with cron.
  """
  if options["now"]:
    # XXX-Cedric: deprecate "--now"
    return

  maximal_delay = int(options.get("maximal_delay", "0"))
  if maximal_delay:
    duration = random.randint(1, maximal_delay)
    logging.info("Sleeping for %s seconds. To disable this feature, " \
                    "check --now parameter in slapgrid help." % duration)
    time.sleep(duration)



def parseArgumentTupleAndReturnSlapgridObject(*argument_tuple):
  """Returns a new instance of slapgrid.Slapgrid created with argument+config parameters.
     Also returns the options dict and unused variable list, and configures logger.
  """
  options = parse_arguments_merge_config(*argument_tuple)

  setup_logger(options)

  check_missing_parameters(options)
  check_missing_files(options)

  if options.get('all'):
    options['develop'] = True

  if options.get('maximum_periodicity') is not None:
    options['force_periodicity'] = True

  # Supervisord configuration location
  if not options.get('supervisord_configuration_path'):
    options['supervisord_configuration_path'] = \
      os.path.join(options['instance_root'], 'etc', 'supervisord.conf')
  # Supervisord socket
  if not options.get('supervisord_socket'):
    options['supervisord_socket'] = \
      os.path.join(options['instance_root'], 'supervisord.socket')

  signature_certificate_list_string = \
    options.get('signature-certificate-list', None)
  if signature_certificate_list_string is not None:
    cert_marker = "-----BEGIN CERTIFICATE-----"
    signature_certificate_list = [
            cert_marker + '\n' + q.strip()
            for q in signature_certificate_list_string.split(cert_marker)
            if q.strip()
            ]
  else:
    signature_certificate_list = None

  # Parse cache / binary cache options
  # Backward compatibility about "binary-cache-url-blacklist" deprecated option
  if options.get("binary-cache-url-blacklist") and not \
      options.get("download-from-binary-cache-url-blacklist"):
    options["download-from-binary-cache-url-blacklist"] = \
        options["binary-cache-url-blacklist"]
  options["download-from-binary-cache-url-blacklist"] = [
      url.strip() for url in options.get(
          "download-from-binary-cache-url-blacklist", "").split('\n') if url]
  options["upload-to-binary-cache-url-blacklist"] = [
      url.strip() for url in options.get(
          "upload-to-binary-cache-url-blacklist", "").split('\n') if url]

  random_delay(options)

  # Return new Slapgrid instance and options
  return ([Slapgrid(software_root=options['software_root'],
            instance_root=options['instance_root'],
            master_url=options['master_url'],
            computer_id=options['computer_id'],
            supervisord_socket=options['supervisord_socket'],
            supervisord_configuration_path=options[
              'supervisord_configuration_path'],
            key_file=options.get('key_file'),
            cert_file=options.get('cert_file'),
            master_ca_file=options.get('master_ca_file'),
            certificate_repository_path=options.get('certificate_repository_path'),
            signature_private_key_file=options.get('signature_private_key_file'),
            signature_certificate_list=signature_certificate_list,
            download_binary_cache_url=\
              options.get('download-binary-cache-url', None),
            upload_binary_cache_url=\
              options.get('upload-binary-cache-url', None),
            download_from_binary_cache_url_blacklist=\
                options.get('download-from-binary-cache-url-blacklist', []),
            upload_to_binary_cache_url_blacklist=\
                options.get('upload-to-binary-cache-url-blacklist', []),
            upload_cache_url=options.get('upload-cache-url', None),
            download_binary_dir_url=\
              options.get('download-binary-dir-url', None),
            upload_binary_dir_url=\
              options.get('upload-binary-dir-url', None),
            upload_dir_url=options.get('upload-dir-url', None),
            buildout=options.get('buildout'),
            promise_timeout=options['promise_timeout'],
            shacache_cert_file=options.get('shacache-cert-file', None),
            shacache_key_file=options.get('shacache-key-file', None),
            shadir_cert_file=options.get('shadir-cert-file', None),
            shadir_key_file=options.get('shadir-key-file', None),
            develop=options.get('develop', False),
            # Try to fetch from deprecated argument
            software_release_filter_list=options.get('only-sr', options.get('only_sr', None)),
            # Try to fetch from deprecated argument
            computer_partition_filter_list=options.get('only-cp', options.get('only_cp', None)),
            force_periodicity = options.get('force_periodicity', False),
            maximum_periodicity = options.get('maximum_periodicity', 86400),
            ),
          options])


def realRun(argument_tuple, method):
  slapgrid_object, options = \
      parseArgumentTupleAndReturnSlapgridObject(*argument_tuple)
  pidfile = options.get('pidfile')
  if pidfile:
    setRunning(pidfile)
  try:
    failed = False
    failed_promise = False
    # Quite complicated way to figure out if everything went fine
    return_value = getattr(slapgrid_object, method)()
    if return_value == SLAPGRID_FAIL:
      failed = True
    if return_value == SLAPGRID_PROMISE_FAIL:
      failed_promise = True
  finally:
    if pidfile:
      setFinished(pidfile)
  if failed:
    sys.exit(SLAPGRID_FAIL)
  if failed_promise:
    sys.exit(SLAPGRID_PROMISE_FAIL)
  sys.exit(SLAPGRID_SUCCESS)


def runSoftwareRelease(*argument_tuple):
  """Hook for entry point to process Software Releases only
  """
  realRun(argument_tuple, 'processSoftwareReleaseList')


def runComputerPartition(*argument_tuple):
  """Hook for entry point to process Computer Partitions only
  """
  realRun(argument_tuple, 'processComputerPartitionList')


def runUsageReport(*argument_tuple):
  """Hook for entry point to process Usage Reports only
  """
  realRun(argument_tuple, 'agregateAndSendUsage')


class Slapgrid(object):
  """ Main class for SlapGrid. Fetches and processes informations from master
  server and pushes usage information to master server.
  """

  class PromiseError(Exception):
    pass

  def __init__(self,
               software_root,
               instance_root,
               master_url,
               computer_id,
               supervisord_socket,
               supervisord_configuration_path,
               buildout,
               force_periodicity=False,
               maximum_periodicity=86400,
               key_file=None,
               cert_file=None,
               signature_private_key_file=None,
               signature_certificate_list=None,
               download_binary_cache_url=None,
               upload_binary_cache_url=None,
               download_from_binary_cache_url_blacklist=None,
               upload_to_binary_cache_url_blacklist=None,
               upload_cache_url=None,
               download_binary_dir_url=None,
               upload_binary_dir_url=None,
               upload_dir_url=None,
               master_ca_file=None,
               certificate_repository_path=None,
               promise_timeout=3,
               shacache_cert_file=None,
               shacache_key_file=None,
               shadir_cert_file=None,
               shadir_key_file=None,
               develop=False,
               software_release_filter_list=None,
               computer_partition_filter_list=None,
               ):
    """Makes easy initialisation of class parameters"""
    # Parses arguments
    self.software_root = os.path.abspath(software_root)
    self.instance_root = os.path.abspath(instance_root)
    self.master_url = master_url
    self.computer_id = computer_id
    self.supervisord_socket = supervisord_socket
    self.supervisord_configuration_path = supervisord_configuration_path
    self.key_file = key_file
    self.cert_file = cert_file
    self.master_ca_file = master_ca_file
    self.certificate_repository_path = certificate_repository_path
    self.signature_private_key_file = signature_private_key_file
    self.signature_certificate_list = signature_certificate_list
    self.download_binary_cache_url = download_binary_cache_url
    self.upload_binary_cache_url = upload_binary_cache_url
    self.download_from_binary_cache_url_blacklist = \
        download_from_binary_cache_url_blacklist
    self.upload_to_binary_cache_url_blacklist = \
        upload_to_binary_cache_url_blacklist
    self.upload_cache_url = upload_cache_url
    self.download_binary_dir_url = download_binary_dir_url
    self.upload_binary_dir_url = upload_binary_dir_url
    self.upload_dir_url = upload_dir_url
    self.shacache_cert_file = shacache_cert_file
    self.shacache_key_file = shacache_key_file
    self.shadir_cert_file = shadir_cert_file
    self.shadir_key_file = shadir_key_file
    # Configures logger
    self.logger = logging.getLogger('Slapgrid')
    # Creates objects from slap module
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.master_url, key_file=self.key_file,
        cert_file=self.cert_file, master_ca_file=self.master_ca_file)
    self.computer = self.slap.registerComputer(self.computer_id)
    # Defines all needed paths
    self.supervisord_configuration_directory = \
        os.path.join(self.instance_root, 'etc', 'supervisord.conf.d')
    self.buildout = buildout
    self.promise_timeout = promise_timeout
    self.develop = develop
    if software_release_filter_list is not None:
      self.software_release_filter_list = \
          software_release_filter_list.split(",")
    else:
      self.software_release_filter_list = []
    self.computer_partition_filter_list = []
    if computer_partition_filter_list is not None:
      self.computer_partition_filter_list = \
          computer_partition_filter_list.split(",")
    self.maximum_periodicity = maximum_periodicity
    self.force_periodicity = force_periodicity

  def getWatchdogLine(self):
    invocation_list = [WATCHDOG_PATH]
    invocation_list.append("--master-url '%s' " % self.master_url)
    if self.certificate_repository_path:
      invocation_list.append("--certificate-repository-path '%s'" \
                               % self.certificate_repository_path)
    invocation_list.append("--computer-id '%s'" % self.computer_id)
    return ' '.join(invocation_list)

  def checkEnvironmentAndCreateStructure(self):
    """Checks for software_root and instance_root existence, then creates
       needed files and directories.
    """
    # Checks for software_root and instance_root existence
    if not os.path.isdir(self.software_root):
      raise OSError('%s does not exist.' % self.software_root)
    if not os.path.isdir(self.instance_root):
      raise OSError('%s does not exist.' % self.instance_root)
    # Creates everything needed

    # Creates instance_root structure
    createPrivateDirectory(os.path.join(self.instance_root, 'var'))
    createPrivateDirectory(os.path.join(self.instance_root, 'var', 'log'))
    createPrivateDirectory(os.path.join(self.instance_root, 'var', 'run'))

    createPrivateDirectory(os.path.join(self.instance_root, 'etc'))
    createPrivateDirectory(self.supervisord_configuration_directory)

    # Creates supervisord configuration
    updateFile(self.supervisord_configuration_path,
      pkg_resources.resource_stream(__name__,
        'templates/supervisord.conf.in').read() % {
            'supervisord_configuration_directory': self.supervisord_configuration_directory,
            'supervisord_socket': os.path.abspath(self.supervisord_socket),
            'supervisord_loglevel': 'info',
            'supervisord_logfile': os.path.abspath(os.path.join(self.instance_root, 'var', 'log', 'supervisord.log')),
            'supervisord_logfile_maxbytes': '50MB',
            'supervisord_nodaemon': 'false',
            'supervisord_pidfile': os.path.abspath(os.path.join(self.instance_root, 'var', 'run', 'supervisord.pid')),
            'supervisord_logfile_backups': '10',
            'watchdog_command': self.getWatchdogLine(),
            })

  def getComputerPartitionList(self):
    try:
      return self.computer.getComputerPartitionList()
    except socket.error as exc:
      self.logger.fatal(exc)
      raise

  def processSoftwareReleaseList(self):
    """Will process each Software Release.
    """
    self.checkEnvironmentAndCreateStructure()
    logger = logging.getLogger('SoftwareReleases')
    logger.info("Processing software releases...")
    # Boolean to know if every instance has correctly been deployed
    clean_run = True
    for software_release in self.computer.getSoftwareReleaseList():
      state = software_release.getState()
      try:
        software_release_uri = software_release.getURI()
        url_hash = md5digest(software_release_uri)
        software_path = os.path.join(self.software_root, url_hash)
        software = Software(url=software_release_uri,
            software_root=self.software_root,
            buildout=self.buildout,
            signature_private_key_file=self.signature_private_key_file,
            signature_certificate_list=self.signature_certificate_list,
            download_binary_cache_url=self.download_binary_cache_url,
            upload_binary_cache_url=self.upload_binary_cache_url,
            download_from_binary_cache_url_blacklist=\
                self.download_from_binary_cache_url_blacklist,
            upload_to_binary_cache_url_blacklist=\
                self.upload_to_binary_cache_url_blacklist,
            upload_cache_url=self.upload_cache_url,
            download_binary_dir_url=self.download_binary_dir_url,
            upload_binary_dir_url=self.upload_binary_dir_url,
            upload_dir_url=self.upload_dir_url,
            shacache_cert_file=self.shacache_cert_file,
            shacache_key_file=self.shacache_key_file,
            shadir_cert_file=self.shadir_cert_file,
            shadir_key_file=self.shadir_key_file)
        if state == 'available':
          completed_tag = os.path.join(software_path, '.completed')
          if self.develop or (not os.path.exists(completed_tag) and \
                 len(self.software_release_filter_list) == 0) or \
                 url_hash in self.software_release_filter_list or \
                 url_hash in (md5digest(uri) for uri in self.software_release_filter_list):
            try:
              software_release.building()
            except NotFoundError:
              pass
            software.install()
            with open(completed_tag, 'w') as fout:
              fout.write(time.asctime())
        elif state == 'destroyed':
          if os.path.exists(software_path):
            logger.info('Destroying %r...' % software_release_uri)
            software.destroy()
            logger.info('Destroyed %r.' % software_release_uri)
      # Send log before exiting
      except (SystemExit, KeyboardInterrupt):
        software_release.error(traceback.format_exc())
        raise

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError as exc:
        clean_run = False
        try:
          software_release.error(exc)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          logger.error('Problem while reporting error, continuing:\n%s' %
                       traceback.format_exc())

      # For everything else: log it, send it, continue.
      except Exception:
        exc = traceback.format_exc()
        logger.error(exc)
        software_release.error(exc)
        clean_run = False
      else:
        if state == 'available':
          try:
            software_release.available()
          except NotFoundError:
            pass
        elif state == 'destroyed':
          try:
            software_release.destroyed()
          except (NotFoundError, ServerError):
            print traceback.format_exc()
    logger.info("Finished software releases.")

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    return SLAPGRID_SUCCESS


  def _launchSupervisord(self):
    launchSupervisord(self.supervisord_socket,
                      self.supervisord_configuration_path,
                      logger=self.logger)

  def _checkPromises(self, computer_partition):
    self.logger.info("Checking promises...")
    instance_path = os.path.join(self.instance_root, computer_partition.getId())

    uid, gid = None, None
    stat_info = os.stat(instance_path)

    #stat sys call to get statistics informations
    uid = stat_info.st_uid
    gid = stat_info.st_gid

    promise_present = False
    # Get the list of promises
    promise_dir = os.path.join(instance_path, 'etc', 'promise')
    if os.path.exists(promise_dir) and os.path.isdir(promise_dir):
      cwd = instance_path
      promises_list = os.listdir(promise_dir)

      # Check whether every promise is kept
      for promise in promises_list:
        promise_present = True

        command = [os.path.join(promise_dir, promise)]

        promise = os.path.basename(command[0])
        self.logger.info("Checking promise %r.", promise)

        process_handler = subprocess.Popen(command,
                                           preexec_fn=lambda: dropPrivileges(uid, gid),
                                           cwd=cwd,
                                           env=None if sys.platform == 'cygwin' else {},
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           stdin=subprocess.PIPE)
        process_handler.stdin.flush()
        process_handler.stdin.close()
        process_handler.stdin = None

        time.sleep(self.promise_timeout)

        if process_handler.poll() is None:
          process_handler.terminate()
          raise Slapgrid.PromiseError("The promise %r timed out" % promise)
        elif process_handler.poll() != 0:
          stderr = process_handler.communicate()[1]
          if stderr is None:
            stderr = 'No error output from %r.' % promise
          else:
            stderr = 'Promise %r:' % promise + stderr
          raise Slapgrid.PromiseError(stderr)

    if not promise_present:
      self.logger.info("No promise.")

  def processComputerPartition(self, computer_partition):
    """
    Process a Computer Partition, depending on its state
    """
    logger = logging.getLogger('ComputerPartitionProcessing')

    computer_partition_id = computer_partition.getId()

    # Sanity checks before processing
    # Those values should not be None or empty string or any falsy value
    if not computer_partition_id:
      raise ValueError('Computer Partition id is empty.')

    # Check if we defined explicit list of partitions to process.
    # If so, if current partition not in this list, skip.
    if len(self.computer_partition_filter_list) > 0 and \
         (computer_partition_id not in self.computer_partition_filter_list):
      return

    logger.info('Processing Computer Partition %s...' % computer_partition_id)

    instance_path = os.path.join(self.instance_root, computer_partition_id)

    # Try to get partition timestamp (last modification date)
    timestamp_path = os.path.join(
        instance_path,
        COMPUTER_PARTITION_TIMESTAMP_FILENAME
    )
    parameter_dict = computer_partition.getInstanceParameterDict()
    if 'timestamp' in parameter_dict:
      timestamp = parameter_dict['timestamp']
    else:
      timestamp = None

    try:
      software_url = computer_partition.getSoftwareRelease().getURI()
    except NotFoundError:
      # Problem with instance: SR URI not set.
      # Try to process it anyway, it may need to be deleted.
      software_url = None
    try:
      software_path = os.path.join(self.software_root, md5digest(software_url))
    except TypeError:
      # Problem with instance: SR URI not set.
      # Try to process it anyway, it may need to be deleted.
      software_path = None

    periodicity = self.maximum_periodicity
    if software_path:
      # Get periodicity from periodicity file if not forced
      if not self.force_periodicity:
        periodicity_path = os.path.join(software_path, 'periodicity')
        if os.path.exists(periodicity_path):
          try:
            periodicity = int(open(periodicity_path).read())
          except ValueError:
            os.remove(periodicity_path)
            logger.error(traceback.format_exc())

    # Check if timestamp from server is more recent than local one.
    # If not: it's not worth processing this partition (nothing has
    # changed).
    if computer_partition_id not in self.computer_partition_filter_list and \
        (not self.develop) and os.path.exists(timestamp_path):
      old_timestamp = open(timestamp_path).read()
      last_runtime = int(os.path.getmtime(timestamp_path))
      if timestamp:
        try:
          if int(timestamp) <= int(old_timestamp):
            if computer_partition.getState() != COMPUTER_PARTITION_STARTED_STATE:
              return
            # Check periodicity, i.e if periodicity is one day, partition
            # should be processed at least every day.
            # Only do it for "started" instances
            if int(time.time()) <= (last_runtime + periodicity):
              self.logger.info('Partition already up-to-date, skipping.')
              return
            else:
              # Periodicity forced processing this partition. Removing
              # the timestamp file in case it fails.
              os.remove(timestamp_path)
        except ValueError:
          os.remove(timestamp_path)
          logger.error(traceback.format_exc())

    local_partition = Partition(
      software_path=software_path,
      instance_path=instance_path,
      supervisord_partition_configuration_path=os.path.join(
        self.supervisord_configuration_directory, '%s.conf' %
        computer_partition_id),
      supervisord_socket=self.supervisord_socket,
      computer_partition=computer_partition,
      computer_id=self.computer_id,
      partition_id=computer_partition_id,
      server_url=self.master_url,
      software_release_url=software_url,
      certificate_repository_path=self.certificate_repository_path,
      buildout=self.buildout)

    computer_partition_state = computer_partition.getState()
    if computer_partition_state == COMPUTER_PARTITION_STARTED_STATE:
      local_partition.install()
      computer_partition.available()
      local_partition.start()
      self._checkPromises(computer_partition)
      computer_partition.started()
    elif computer_partition_state == COMPUTER_PARTITION_STOPPED_STATE:
      try:
        local_partition.install()
        computer_partition.available()
      except Exception:
        raise
      finally:
        # Instance has to be stopped even if buildout/reporting is wrong.
        local_partition.stop()
      computer_partition.stopped()
    elif computer_partition_state == COMPUTER_PARTITION_DESTROYED_STATE:
      local_partition.stop()
      try:
        computer_partition.stopped()
      except (SystemExit, KeyboardInterrupt):
        computer_partition.error(traceback.format_exc())
        raise
      except Exception:
        pass
    else:
      error_string = "Computer Partition %r has unsupported state: %s" % \
        (computer_partition_id, computer_partition_state)
      computer_partition.error(error_string)
      raise NotImplementedError(error_string)

    # If partition has been successfully processed, write timestamp
    if timestamp:
      timestamp_path = os.path.join(
          instance_path,
          COMPUTER_PARTITION_TIMESTAMP_FILENAME
      )
      open(timestamp_path, 'w').write(timestamp)

  def FilterComputerPartitionList(self, computer_partition_list):
    """
    Try to filter valid partitions to be processed from free partitions.
    """
    logger = logging.getLogger('ComputerPartitionProcessing')
    filtered_computer_partition_list = []
    for computer_partition in computer_partition_list:
      try:
        computer_partition_path = os.path.join(self.instance_root,
            computer_partition.getId())
        if not os.path.exists(computer_partition_path):
          raise NotFoundError('Partition directory %s does not exist.' %
              computer_partition_path)
        # Check state of partition. If it is in "destroyed" state, check if it
        # partition is actually installed in the Computer or if it is "free"
        # partition, and check if it has some Software information.
        # XXX-Cedric: Temporary AND ugly solution to check if an instance
        # is in the partition. Dangerous because not 100% sure it is empty
        computer_partition_state = computer_partition.getState()
        try:
          software_url = computer_partition.getSoftwareRelease().getURI()
        except (NotFoundError, TypeError, NameError):
          software_url = None
        if computer_partition_state == COMPUTER_PARTITION_DESTROYED_STATE and \
           os.listdir(computer_partition_path) == [] and \
           not software_url:
          continue

        # Everything seems fine
        filtered_computer_partition_list.append(computer_partition)

      # XXX-Cedric: factor all this error handling

      # Send log before exiting
      except (SystemExit, KeyboardInterrupt):
        computer_partition.error(traceback.format_exc())
        raise

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError as exc:
        try:
          computer_partition.error(exc)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          logger.error('Problem during reporting error, continuing:\n%s' %
                       traceback.format_exc())

      # For everything else: log it, send it, continue.
      except Exception as exc:
        logger.error(traceback.format_exc())
        try:
          computer_partition.error(exc)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          logger.error('Problem during reporting error, continuing:\n%s' %
                       traceback.format_exc())

    return filtered_computer_partition_list

  def processComputerPartitionList(self):
    """
    Will start supervisord and process each Computer Partition.
    """
    logger = logging.getLogger('ComputerPartitionProcessing')
    logger.info('Processing computer partitions...')
    # Prepares environment
    self.checkEnvironmentAndCreateStructure()
    self._launchSupervisord()

    # Boolean to know if every instance has correctly been deployed
    clean_run = True
    # Boolean to know if every promises correctly passed
    clean_run_promise = True

    # Filter all dummy / empty partitions
    computer_partition_list = self.FilterComputerPartitionList(
        self.getComputerPartitionList())

    for computer_partition in computer_partition_list:
      # Nothing should raise outside of the current loop iteration, so that
      # even if something is terribly wrong while processing an instance, it
      # won't prevent processing other ones.
      try:
        # Process the partition itself
        self.processComputerPartition(computer_partition)

      # Send log before exiting
      except (SystemExit, KeyboardInterrupt):
        computer_partition.error(traceback.format_exc())
        raise

      except Slapgrid.PromiseError as exc:
        clean_run_promise = False
        try:
          logger.error(exc)
          computer_partition.error(exc)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          logger.error('Problem during reporting error, continuing:\n%s' %
                       traceback.format_exc())

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError as exc:
        clean_run = False
        try:
          computer_partition.error(exc)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          logger.error('Problem during reporting error, continuing:\n%s' %
                       traceback.format_exc())

      # For everything else: log it, send it, continue.
      except Exception as exc:
        clean_run = False
        logger.error(traceback.format_exc())
        try:
          computer_partition.error(exc)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          logger.error('Problem during reporting error, continuing:\n%s' %
                       traceback.format_exc())

    logger.info("Finished computer partitions.")

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    if not clean_run_promise:
      return SLAPGRID_PROMISE_FAIL
    return SLAPGRID_SUCCESS


  def validateXML(self, to_be_validated, xsd_model):
    """Validates a given xml file"""

    logger = logging.getLogger('XMLValidating')

    #We retrieve the xsd model
    xsd_model = StringIO.StringIO(xsd_model)
    xmlschema_doc = etree.parse(xsd_model)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    try:
      document = etree.fromstring(to_be_validated)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as exc:
      logger.info('Failed to parse this XML report :  %s\n%s' % \
        (to_be_validated, _formatXMLError(exc)))
      logger.error(_formatXMLError(exc))
      return False

    if xmlschema.validate(document):
      return True

    return False

  def asXML(self, computer_partition_usage_list):
    """Generates a XML report from computer partition usage list
    """
    xml = ['<?xml version="1.0"?>',
           '<journal>',
           '<transaction type="Sale Packing List">',
           '<title>Resource consumptions</title>',
           '<start_date></start_date>',
           '<stop_date>%s</stop_date>' % time.strftime("%Y-%m-%d at %H:%M:%S"),
           '<reference>%s</reference>' % self.computer_id,
           '<currency></currency>',
           '<payment_mode></payment_mode>',
           '<category></category>',
           '<arrow type="Administration">',
           '<source></source>',
           '<destination></destination>',
           '</arrow>']

    for computer_partition_usage in computer_partition_usage_list:
      try:
        root = etree.fromstring(computer_partition_usage.usage)
      except UnicodeError as exc:
        self.logger.info("Failed to read %s." % computer_partition_usage.usage)
        self.logger.error(UnicodeError)
        raise UnicodeError("Failed to read %s: %s" % (computer_partition_usage.usage, exc))
      except (etree.XMLSyntaxError, etree.DocumentInvalid) as exc:
        self.logger.info("Failed to parse %s." % (computer_partition_usage.usage))
        self.logger.error(exc)
        raise _formatXMLError(exc)
      except Exception as exc:
        raise Exception("Failed to generate XML report: %s" % exc)

      for movement in root.findall('movement'):
        xml.append('<movement>')
        for child in movement.getchildren():
          if child.tag == "reference":
            xml.append('<%s>%s</%s>' % (child.tag, computer_partition_usage.getId(), child.tag))
          else:
            xml.append('<%s>%s</%s>' % (child.tag, child.text, child.tag))
        xml.append('</movement>')

    xml.append('</transaction></journal>')

    return ''.join(xml)

  def agregateAndSendUsage(self):
    """Will agregate usage from each Computer Partition.
    """
    # Prepares environment
    self.checkEnvironmentAndCreateStructure()
    self._launchSupervisord()

    slap_computer_usage = self.slap.registerComputer(self.computer_id)
    computer_partition_usage_list = []
    logger = logging.getLogger('UsageReporting')
    logger.info("Aggregating and sending usage reports...")

    #We retrieve XSD models
    try:
      computer_consumption_model = \
        pkg_resources.resource_string(
          'slapos.slap',
          'doc/computer_consumption.xsd')
    except IOError:
      computer_consumption_model = \
        pkg_resources.resource_string(
          __name__,
          '../../../../slapos/slap/doc/computer_consumption.xsd')

    try:
      partition_consumption_model = \
        pkg_resources.resource_string(
          'slapos.slap',
          'doc/partition_consumption.xsd')
    except IOError:
      partition_consumption_model = \
        pkg_resources.resource_string(
          __name__,
          '../../../../slapos/slap/doc/partition_consumption.xsd')

    clean_run = True
    # Loop on the different computer partitions
    computer_partition_list = self.FilterComputerPartitionList(
       slap_computer_usage.getComputerPartitionList())

    for computer_partition in computer_partition_list:
      try:
        computer_partition_id = computer_partition.getId()

        #We want execute all the script in the report folder
        instance_path = os.path.join(self.instance_root,
            computer_partition.getId())
        report_path = os.path.join(instance_path, 'etc', 'report')
        if os.path.isdir(report_path):
          script_list_to_run = os.listdir(report_path)
        else:
          script_list_to_run = []

        #We now generate the pseudorandom name for the xml file
        # and we add it in the invocation_list
        f = tempfile.NamedTemporaryFile()
        name_xml = '%s.%s' % ('slapreport', os.path.basename(f.name))
        path_to_slapreport = os.path.join(instance_path, 'var', 'xml_report',
            name_xml)

        failed_script_list = []
        for script in script_list_to_run:
          invocation_list = []
          invocation_list.append(os.path.join(instance_path, 'etc', 'report',
            script))
          #We add the xml_file name in the invocation_list
          #f = tempfile.NamedTemporaryFile()
          #name_xml = '%s.%s' % ('slapreport', os.path.basename(f.name))
          #path_to_slapreport = os.path.join(instance_path, 'var', name_xml)

          invocation_list.append(path_to_slapreport)
          #Dropping privileges
          uid, gid = None, None
          stat_info = os.stat(instance_path)
          #stat sys call to get statistics informations
          uid = stat_info.st_uid
          gid = stat_info.st_gid
          process_handler = SlapPopen(invocation_list,
                                      preexec_fn=lambda: dropPrivileges(uid, gid),
                                      cwd=os.path.join(instance_path, 'etc', 'report'),
                                      env=None,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
          if process_handler.returncode is None:
            process_handler.kill()
          if process_handler.returncode != 0:
            clean_run = False
            failed_script_list.append("Script %r failed." % script)
            logger.warning("Failed to run %r" % invocation_list)
          if len(failed_script_list):
            computer_partition.error('\n'.join(failed_script_list))
      # Whatever happens, don't stop processing other instances
      except Exception:
        logger.info('Cannot run usage script(s) for %r: %s' % (
                      computer_partition.getId(),
                      traceback.format_exc()))

    #Now we loop through the different computer partitions to report
    report_usage_issue_cp_list = []
    for computer_partition in computer_partition_list:
      try:
        filename_delete_list = []
        computer_partition_id = computer_partition.getId()
        instance_path = os.path.join(self.instance_root, computer_partition_id)
        dir_reports = os.path.join(instance_path, 'var', 'xml_report')
        #The directory xml_report contain a number of files equal
        #to the number of software instance running inside the same partition
        if os.path.isdir(dir_reports):
          filename_list = os.listdir(dir_reports)
        else:
          filename_list = []
        #logger.debug('name List %s' % filename_list)

        for filename in filename_list:

          file_path = os.path.join(dir_reports, filename)
          if os.path.exists(file_path):
            usage = open(file_path, 'r').read()

            #We check the validity of xml content of each reports
            if not self.validateXML(usage, partition_consumption_model):
              logger.info('WARNING: The XML file %s generated by slapreport is '
                  'not valid - This report is left as is at %s where you can '
                  'inspect what went wrong ' % (filename, dir_reports))
              # Warn the SlapOS Master that a partition generates corrupted xml
              # report
            else:
              computer_partition_usage = self.slap.registerComputerPartition(
                      self.computer_id, computer_partition_id)
              computer_partition_usage.setUsage(usage)
              computer_partition_usage_list.append(computer_partition_usage)
              filename_delete_list.append(filename)
          else:
            logger.debug("Usage report %r not found, ignored" % file_path)

        #After sending the aggregated file we remove all the valid xml reports
        for filename in filename_delete_list:
          os.remove(os.path.join(dir_reports, filename))

      # Whatever happens, don't stop processing other instances
      except Exception:
        logger.info('Cannot run usage script(s) for %r: %s' % (
                      computer_partition.getId(),
                      traceback.format_exc()))

    for computer_partition_usage in computer_partition_usage_list:
      logger.info('computer_partition_usage_list: %s - %s' % (
                    computer_partition_usage.usage,
                    computer_partition_usage.getId()))

    #If there is, at least, one report
    if computer_partition_usage_list != []:
      try:
        #We generate the final XML report with asXML method
        computer_consumption = self.asXML(computer_partition_usage_list)

        logger.info('Final xml report: %s' % computer_consumption)

        #We test the XML report before sending it
        if self.validateXML(computer_consumption, computer_consumption_model):
          logger.info('XML file generated by asXML is valid')
          slap_computer_usage.reportUsage(computer_consumption)
        else:
          logger.info('XML file generated by asXML is not valid !')
          raise ValueError('XML file generated by asXML is not valid !')
      except Exception:
        issue = "Cannot report usage for %r: %s" % (
                    computer_partition.getId(),
                    traceback.format_exc())
        logger.info(issue)
        computer_partition.error(issue)
        report_usage_issue_cp_list.append(computer_partition_id)

    for computer_partition in computer_partition_list:
      if computer_partition.getState() == COMPUTER_PARTITION_DESTROYED_STATE:
        try:
          computer_partition_id = computer_partition.getId()
          try:
             software_url = computer_partition.getSoftwareRelease().getURI()
             software_path = os.path.join(self.software_root, md5digest(software_url))
          except (NotFoundError, TypeError):
            software_url = None
            software_path = None

          local_partition = Partition(
            software_path=software_path,
            instance_path=os.path.join(self.instance_root,
                computer_partition.getId()),
            supervisord_partition_configuration_path=os.path.join(
              self.supervisord_configuration_directory, '%s.conf' %
              computer_partition_id),
            supervisord_socket=self.supervisord_socket,
            computer_partition=computer_partition,
            computer_id=self.computer_id,
            partition_id=computer_partition_id,
            server_url=self.master_url,
            software_release_url=software_url,
            certificate_repository_path=self.certificate_repository_path,
            buildout=self.buildout,
            )
          local_partition.stop()
          try:
            computer_partition.stopped()
          except (SystemExit, KeyboardInterrupt):
            computer_partition.error(traceback.format_exc())
            raise
          except Exception:
            pass
          if computer_partition.getId() in report_usage_issue_cp_list:
            logger.info('Ignoring destruction of %r, as no report usage was sent' %
                        computer_partition.getId())
            continue
          local_partition.destroy()
        except (SystemExit, KeyboardInterrupt):
          computer_partition.error(traceback.format_exc())
          raise
        except Exception:
          clean_run = False
          exc = traceback.format_exc()
          computer_partition.error(exc)
          logger.error(exc)
        try:
          computer_partition.destroyed()
        except NotFoundError:
          logger.debug('Ignored slap error while trying to inform about '
              'destroying not fully configured Computer Partition %r' %
                  computer_partition.getId())
        except ServerError as server_error:
          logger.debug('Ignored server error while trying to inform about '
              'destroying Computer Partition %r. Error is:\n%r' %
                  (computer_partition.getId(), server_error.args[0]))

    logger.info("Finished usage reports.")

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    return SLAPGRID_SUCCESS
