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
from exception import BuildoutFailedError
from hashlib import md5
from lxml import etree
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
  warnings.warn('Used python version (%s) is old and have problems with'
      ' IPv6 connections' % sys.version.split('\n')[0])

from slapos.slap.slap import NotFoundError
from slapos.slap.slap import ServerError
from SlapObject import Software, Partition, WrongPermissionError, \
    PathDoesNotExistError
from svcbackend import launchSupervisord
from utils import createPrivateDirectory
from utils import dropPrivileges
from utils import getSoftwareUrlHash
from utils import setRunning
from utils import setFinished
from utils import SlapPopen
from utils import updateFile
from slapos import slap

MANDATORY_PARAMETER_LIST = [
    'computer_id',
    'instance_root',
    'master_url',
    'software_root',
]

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


class _formatXMLError(Exception):
  pass


def parseArgumentTupleAndReturnSlapgridObject(*argument_tuple):
  """Parses arguments either from command line, from method parameters or from
     config file. Then returns a new instance of slapgrid.Slapgrid with those
     parameters. Also returns the options dict and unused variable list, and
     configures logger.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("--instance-root",
      help="The instance root directory location.")
  parser.add_argument("--software-root",
      help="The software_root directory location.")
  parser.add_argument("--master-url",
      help="The master server URL. Mandatory.")
  parser.add_argument("--computer-id",
      help="The computer id defined in the server.")
  parser.add_argument("--supervisord-socket",
      help="The socket supervisor will use.")
  parser.add_argument("--supervisord-configuration-path",
      help="The location where supervisord configuration will be stored.")
  parser.add_argument("--buildout", default=None,
      help="Location of buildout binary.")
  parser.add_argument("--pidfile",
      help="The location where pidfile will be created.")
  parser.add_argument("--logfile",
      help="The location where slapgrid logfile will be created.")
  parser.add_argument("--key_file", help="SSL Authorisation key file.")
  parser.add_argument("--cert_file",
      help="SSL Authorisation certificate file.")
  parser.add_argument("--signature_private_key_file",
      help="Signature private key file.")
  parser.add_argument("--master_ca_file",
      help="Root certificate of SlapOS master key.")
  parser.add_argument("--certificate_repository_path",
      help="Path to directory where downloaded certificates would be stored.")
  parser.add_argument("-c", "--console", action="store_true", default=False,
      help="Deprecated, doesn't do anything.")
  parser.add_argument("-v", "--verbose", action="store_true", default=False,
      help="Be verbose.")
  parser.add_argument("--maximum-periodicity", type=int, default=None,
      help="Periodicity at which buildout should be run in instance.")
  parser.add_argument("--promise-timeout", type=int, default=3,
      help="Promise timeout in seconds.")
  parser.add_argument("--now", action="store_true", default=False,
      help="Launch slapgrid without delay. Default behavior.")
  parser.add_argument("--all", action="store_true", default=False,
      help="Launch slapgrid to process all Softare Releases "
           "and/or Computer Partitions.")
  parser.add_argument("--only-sr",
      help="Force the update of a single software release (use url hash), "
           "even if is already installed. This option will make all others "
           "sofware releases be ignored.")
  parser.add_argument("--only-cp",
      help="Update a single or a list of computer partitions "
           "(ie.:slappartX, slappartY),"
           "this option will make all others computer partitions be ignored.")

  parser.add_argument("configuration_file", nargs=1, type=argparse.FileType(),
      help="SlapOS configuration file.")

  # Deprecated options
  parser.add_argument("--develop", action="store_true", default=False,
      help="Deprecated, same as --all.")
  parser.add_argument("--only_sr",
      help="Deprecated, same as --only-sr.")
  parser.add_argument("--only_cp",
      help="Deprecated, same as --only-cp.")
  parser.add_argument("--maximal_delay",
      help="Deprecated. Will only work from configuration file in the future.")


  # Parses arguments
  if argument_tuple == ():
    # No arguments given to entry point : we parse sys.argv.
    argument_option_instance = parser.parse_args()
  else:
    argument_option_instance = \
      parser.parse_args(list(argument_tuple))
  # Parses arguments from config file, if needed, then merge previous arguments
  option_dict = {}
  configuration_file = argument_option_instance.configuration_file[0]
  # Loads config (if config specified)
  slapgrid_configuration = ConfigParser.SafeConfigParser()
  slapgrid_configuration.readfp(configuration_file)
  # Merges the two dictionnaries
  option_dict = dict(slapgrid_configuration.items("slapos"))
  if slapgrid_configuration.has_section("networkcache"):
    option_dict.update(dict(slapgrid_configuration.items("networkcache")))
  for argument_key, argument_value in vars(argument_option_instance
      ).iteritems():
    if argument_value is not None:
      option_dict.update({argument_key: argument_value})
  # Configures logger.
  if option_dict['verbose']:
    level = logging.DEBUG
  else:
    level = logging.INFO
  logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                      level=level,
                      datefmt='%Y-%m-%dT%H:%M:%S')
  if option_dict.get('logfile'):
    console = logging.FileHandler(option_dict['logfile'])
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        '%(asctime)s %(name)-18s: %(levelname)-8s %(message)s'))
    logging.getLogger('').addHandler(console)

  missing_mandatory_parameter_list = []
  for mandatory_parameter in MANDATORY_PARAMETER_LIST:
    if not mandatory_parameter in option_dict:
      missing_mandatory_parameter_list.append(mandatory_parameter)

  if option_dict.get('all') is True:
    option_dict['develop'] = True

  if option_dict.get('maximum_periodicity') is not None:
    option_dict['force_periodicity'] = True

  repository_required = False
  if 'key_file' in option_dict:
    repository_required = True
    if not 'cert_file' in option_dict:
      missing_mandatory_parameter_list.append('cert_file')
  if 'cert_file' in option_dict:
    repository_required = True
    if not 'key_file' in option_dict:
      missing_mandatory_parameter_list.append('key_file')
  if repository_required:
    if 'certificate_repository_path' not in option_dict:
      missing_mandatory_parameter_list.append('certificate_repository_path')

  if len(missing_mandatory_parameter_list) > 0:
    parser.error('Missing mandatory parameters:\n%s' % '\n'.join(
      missing_mandatory_parameter_list))

  key_file = option_dict.get('key_file')
  cert_file = option_dict.get('cert_file')
  master_ca_file = option_dict.get('master_ca_file')
  signature_private_key_file = option_dict.get('signature_private_key_file')

  mandatory_file_list = [key_file, cert_file, master_ca_file]
  # signature_private_key_file is not mandatory, we must be able to run
  # slapgrid scripts without this parameter.
  if signature_private_key_file:
    mandatory_file_list.append(signature_private_key_file)

  for k in ['shacache-cert-file', 'shacache-key-file', 'shadir-cert-file',
      'shadir-key-file']:
    mandatory_file_list.append(option_dict.get(k, None))

  for f in mandatory_file_list:
    if f is not None:
      if not os.path.exists(f):
        parser.error('File %r does not exist.' % f)

  certificate_repository_path = option_dict.get('certificate_repository_path')
  if certificate_repository_path is not None:
    if not os.path.isdir(certificate_repository_path):
      parser.error('Directory %r does not exist' %
          certificate_repository_path)

  # Supervisord configuration location
  if not option_dict.get('supervisord_configuration_path'):
    option_dict['supervisord_configuration_path'] = \
      os.path.join(option_dict['instance_root'], 'etc', 'supervisord.conf')
  # Supervisord socket
  if not option_dict.get('supervisord_socket'):
    option_dict['supervisord_socket'] = \
      os.path.join(option_dict['instance_root'], 'supervisord.socket')

  signature_certificate_list_string = \
    option_dict.get('signature-certificate-list', None)
  if signature_certificate_list_string is not None:
    cert_marker = "-----BEGIN CERTIFICATE-----"
    signature_certificate_list = [cert_marker + '\n' + q.strip() \
      for q in signature_certificate_list_string.split(cert_marker) \
        if q.strip()]
  else:
    signature_certificate_list = None

  # Parse cache / binary cache options
  # Backward compatibility about "binary-cache-url-blacklist" deprecated option
  if option_dict.get("binary-cache-url-blacklist") and not \
      option_dict.get("download-from-binary-cache-url-blacklist"):
    option_dict["download-from-binary-cache-url-blacklist"] = \
        option_dict["binary-cache-url-blacklist"]
  option_dict["download-from-binary-cache-url-blacklist"] = [
      url.strip() for url in option_dict.get(
          "download-from-binary-cache-url-blacklist", "").split('\n') if url]
  option_dict["upload-to-binary-cache-url-blacklist"] = [
      url.strip() for url in option_dict.get(
          "upload-to-binary-cache-url-blacklist", "").split('\n') if url]

  # Sleep for a random time to avoid SlapOS Master being DDOSed by an army of
  # SlapOS Nodes configured with cron.
  if option_dict["now"]:
    # XXX-Cedric: deprecate "--now"
    maximal_delay = 0
  else:
    maximal_delay = int(option_dict.get("maximal_delay", "0"))
  if maximal_delay > 0:
    duration = random.randint(1, maximal_delay)
    logging.info("Sleeping for %s seconds. To disable this feature, " \
                    "check --now parameter in slapgrid help." % duration)
    time.sleep(duration)

  # Return new Slapgrid instance and options
  return ([Slapgrid(software_root=option_dict['software_root'],
            instance_root=option_dict['instance_root'],
            master_url=option_dict['master_url'],
            computer_id=option_dict['computer_id'],
            supervisord_socket=option_dict['supervisord_socket'],
            supervisord_configuration_path=option_dict[
              'supervisord_configuration_path'],
            key_file=key_file,
            cert_file=cert_file,
            master_ca_file=master_ca_file,
            certificate_repository_path=certificate_repository_path,
            signature_private_key_file=signature_private_key_file,
            signature_certificate_list=signature_certificate_list,
            download_binary_cache_url=\
              option_dict.get('download-binary-cache-url', None),
            upload_binary_cache_url=\
              option_dict.get('upload-binary-cache-url', None),
            download_from_binary_cache_url_blacklist=\
                option_dict.get('download-from-binary-cache-url-blacklist', []),
            upload_to_binary_cache_url_blacklist=\
                option_dict.get('upload-to-binary-cache-url-blacklist', []),
            upload_cache_url=option_dict.get('upload-cache-url', None),
            download_binary_dir_url=\
              option_dict.get('download-binary-dir-url', None),
            upload_binary_dir_url=\
              option_dict.get('upload-binary-dir-url', None),
            upload_dir_url=option_dict.get('upload-dir-url', None),
            buildout=option_dict.get('buildout'),
            promise_timeout=option_dict['promise_timeout'],
            shacache_cert_file=option_dict.get('shacache-cert-file', None),
            shacache_key_file=option_dict.get('shacache-key-file', None),
            shadir_cert_file=option_dict.get('shadir-cert-file', None),
            shadir_key_file=option_dict.get('shadir-key-file', None),
            develop=option_dict.get('develop', False),
            software_release_filter_list=option_dict.get('only-sr',
                # Try to fetch from deprecated argument
                option_dict.get('only_sr', None)),
            computer_partition_filter_list=option_dict.get('only-cp',
                # Try to fetch from deprecated argument
                option_dict.get('only_cp', None)),
            force_periodicity = option_dict.get('force_periodicity', False),
            maximum_periodicity = option_dict.get('maximum_periodicity', 86400),
            ),
          option_dict])


def realRun(argument_tuple, method_list):
  slapgrid_object, option_dict = \
      parseArgumentTupleAndReturnSlapgridObject(*argument_tuple)
  pidfile = option_dict.get('pidfile')
  if pidfile:
    setRunning(pidfile)
  try:
    failed = False
    failed_promise = False
    for method in method_list:
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


def run(*argument_tuple):
  """Hooks for generic entry point to proces Software Releases (sr),
     Computer Partitions (cp) and Usage Reports (ur)
     Will run one by one each task (sr, cp, ur). If specified,
     will run in the user wanted order.
  """
  realRun(argument_tuple, ['processSoftwareReleaseList',
    'processComputerPartitionList', 'agregateAndSendUsage'])


def runSoftwareRelease(*argument_tuple):
  """Hook for entry point to process Software Releases only
  """
  realRun(argument_tuple, ['processSoftwareReleaseList'])


def runComputerPartition(*argument_tuple):
  """Hook for entry point to process Computer Partitions only
  """
  realRun(argument_tuple, ['processComputerPartitionList'])


def runUsageReport(*argument_tuple):
  """Hook for entry point to process Usage Reports only
  """
  realRun(argument_tuple, ['agregateAndSendUsage'])


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
    self.slap = slap.slap()
    self.slap.initializeConnection(self.master_url, key_file=self.key_file,
        cert_file=self.cert_file, master_ca_file=self.master_ca_file)
    self.computer = self.slap.registerComputer(self.computer_id)
    # Defines all needed paths
    self.instance_etc_directory = os.path.join(self.instance_root, 'etc')
    self.supervisord_configuration_directory = \
        os.path.join(self.instance_etc_directory, 'supervisord.conf.d')
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
    if self.certificate_repository_path is not None:
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
      error = "%s does not exist." % self.software_root
      raise OSError(error)
    if not os.path.isdir(self.instance_root):
      error = "%s does not exist." % self.instance_root
      raise OSError(error)
    # Creates everything needed
    try:
      # Creates instance_root structure
      createPrivateDirectory(self.instance_etc_directory)
      createPrivateDirectory(os.path.join(self.instance_root, 'var'))
      createPrivateDirectory(os.path.join(self.instance_root, 'var', 'log'))
      createPrivateDirectory(os.path.join(self.instance_root, 'var', 'run'))
      createPrivateDirectory(self.supervisord_configuration_directory)
      # Creates supervisord configuration
      updateFile(self.supervisord_configuration_path,
        pkg_resources.resource_stream(__name__,
          'templates/supervisord.conf.in').read() % dict(
            supervisord_configuration_directory=\
                self.supervisord_configuration_directory,
            supervisord_socket=os.path.abspath(self.supervisord_socket),
            supervisord_loglevel='info',
            supervisord_logfile=os.path.abspath(os.path.join(
              self.instance_root, 'var', 'log', 'supervisord.log')),
            supervisord_logfile_maxbytes='50MB',
            supervisord_nodaemon='false',
            supervisord_pidfile=os.path.abspath(os.path.join(
              self.instance_root, 'var', 'run', 'supervisord.pid')),
            supervisord_logfile_backups='10',
            watchdog_command = self.getWatchdogLine(),
          ))
    except (WrongPermissionError, PathDoesNotExistError) as error:
      raise error

  def getComputerPartitionList(self):
    try:
      computer_partition_list = self.computer.getComputerPartitionList()
    except socket.error as error:
      self.logger.fatal(error)
      raise
    return computer_partition_list

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
        url_hash = md5(software_release_uri).hexdigest()
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
                 url_hash in (md5(uri).hexdigest() for uri in self.software_release_filter_list):
            try:
              software_release.building()
            except NotFoundError:
              pass
            software.install()
            file_descriptor = open(completed_tag, 'w')
            file_descriptor.write(time.asctime())
            file_descriptor.close()
        elif state == 'destroyed':
          if os.path.exists(software_path):
            logger.info('Destroying %r...' % software_release_uri)
            software.destroy()
            logger.info('Destroyed %r.' % software_release_uri)
      # Send log before exiting
      except (SystemExit, KeyboardInterrupt):
        exception = traceback.format_exc()
        software_release.error(exception)
        raise

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError as exception:
        clean_run = False
        try:
          software_release.error(exception)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          exception = traceback.format_exc()
          logger.error('Problem during reporting error, continuing:\n' +
            exception)

      # For everything else: log it, send it, continue.
      except Exception:
        exception = traceback.format_exc()
        logger.error(exception)
        software_release.error(exception)
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
        self.supervisord_configuration_path)

  def _checkPromises(self, computer_partition):
    self.logger.info("Checking promises...")
    instance_path = os.path.join(self.instance_root,
        computer_partition.getId())

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

        kw = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)

        process_handler = subprocess.Popen(command,
          preexec_fn=lambda: dropPrivileges(uid, gid),
          cwd=cwd,
          env={}, **kw)
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
    timestamp_path = os.path.join(instance_path, '.timestamp')
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
      software_path = os.path.join(self.software_root,
          getSoftwareUrlHash(software_url))
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
            exception = traceback.format_exc()
            logger.error(exception)

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
          exception = traceback.format_exc()
          logger.error(exception)

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
        exception = traceback.format_exc()
        computer_partition.error(exception)
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
      timestamp_path = os.path.join(instance_path, '.timestamp')
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
        exception = traceback.format_exc()
        computer_partition.error(exception)
        raise

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError, exception:
        try:
          computer_partition.error(exception)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          exception = traceback.format_exc()
          logger.error('Problem during reporting error, continuing:\n' +
            exception)

      # For everything else: log it, send it, continue.
      except Exception as exception:
        logger.error(traceback.format_exc())
        try:
          computer_partition.error(exception)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          exception = traceback.format_exc()
          logger.error('Problem during reporting error, continuing:\n' +
            exception)

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
        exception = traceback.format_exc()
        computer_partition.error(exception)
        raise

      except Slapgrid.PromiseError as exception:
        clean_run_promise = False
        try:
          logger.error(exception)
          computer_partition.error(exception)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          exception = traceback.format_exc()
          logger.error('Problem during reporting error, continuing:\n' +
            exception)

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError, exception:
        clean_run = False
        try:
          computer_partition.error(exception)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          exception = traceback.format_exc()
          logger.error('Problem during reporting error, continuing:\n' +
            exception)

      # For everything else: log it, send it, continue.
      except Exception as exception:
        clean_run = False
        logger.error(traceback.format_exc())
        try:
          computer_partition.error(exception)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          exception = traceback.format_exc()
          logger.error('Problem during reporting error, continuing:\n' +
            exception)

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
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
      logger.info('Failed to parse this XML report :  %s\n%s' % \
        (to_be_validated, _formatXMLError(e)))
      logger.error(_formatXMLError(e))
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
      except UnicodeError, e:
        self.logger.info("Failed to read %s." % (
            computer_partition_usage.usage))
        self.logger.error(UnicodeError)
        raise UnicodeError("Failed to read %s: %s" % (computer_partition_usage.usage, e))
      except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
        self.logger.info("Failed to parse %s." % (computer_partition_usage.usage))
        self.logger.error(e)
        raise _formatXMLError(e)
      except Exception, e:
        raise Exception("Failed to generate XML report: %s" % e)

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
          kw = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
          process_handler = SlapPopen(invocation_list,
            preexec_fn=lambda: dropPrivileges(uid, gid),
            cwd=os.path.join(instance_path, 'etc', 'report'),
            env=None, **kw)
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
        computer_partition_id = computer_partition.getId()
        exception = traceback.format_exc()
        issue = "Cannot run usage script(s) for %r: %s" % (
            computer_partition_id, exception)
        logger.info(issue)

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
        usage = ''
        
        for filename in filename_list:
        
          file_path = os.path.join(dir_reports, filename)
          if os.path.exists(file_path):
            usage_file = open(file_path, 'r')
            usage = usage_file.read()
            usage_file.close()
        
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
        computer_partition_id = computer_partition.getId()
        exception = traceback.format_exc()
        issue = "Cannot run usage script(s) for %r: %s" % (
            computer_partition_id, exception)
        logger.info(issue)

    for computer_partition_usage in computer_partition_usage_list:
      logger.info('computer_partition_usage_list : %s - %s' % \
        (computer_partition_usage.usage, computer_partition_usage.getId()))

    #If there is, at least, one report
    if computer_partition_usage_list != []:
      try:
        #We generate the final XML report with asXML method
        computer_consumption = self.asXML(computer_partition_usage_list)

        logger.info('Final xml report : %s' % computer_consumption)

        #We test the XML report before sending it
        if self.validateXML(computer_consumption, computer_consumption_model):
          logger.info('XML file generated by asXML is valid')
          slap_computer_usage.reportUsage(computer_consumption)
        else:
          logger.info('XML file generated by asXML is not valid !')
          raise ValueError('XML file generated by asXML is not valid !')
      except Exception:
        computer_partition_id = computer_partition.getId()
        exception = traceback.format_exc()
        issue = "Cannot report usage for %r: %s" % (computer_partition_id,
          exception)
        logger.info(issue)
        computer_partition.error(issue)
        report_usage_issue_cp_list.append(computer_partition_id)

    for computer_partition in computer_partition_list:
      if computer_partition.getState() == COMPUTER_PARTITION_DESTROYED_STATE:
        try:
          computer_partition_id = computer_partition.getId()
          try:
             software_url = computer_partition.getSoftwareRelease().getURI()
             software_path = os.path.join(self.software_root,
                 getSoftwareUrlHash(software_url))
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
            exception = traceback.format_exc()
            computer_partition.error(exception)
            raise
          except Exception:
            pass
          if computer_partition.getId() in report_usage_issue_cp_list:
            logger.info('Ignoring destruction of %r, as not report usage was '
              'sent' % computer_partition.getId())
            continue
          local_partition.destroy()
        except (SystemExit, KeyboardInterrupt):
          exception = traceback.format_exc()
          computer_partition.error(exception)
          raise
        except Exception:
          clean_run = False
          exception = traceback.format_exc()
          computer_partition.error(exception)
          logger.error(exception)
        try:
          computer_partition.destroyed()
        except slap.NotFoundError:
          logger.debug('Ignored slap error while trying to inform about '
              'destroying not fully configured Computer Partition %r' %
                  computer_partition.getId())
        except ServerError as server_error:
          logger.debug('Ignored server error while trying to inform about '
              'destroying Computer Partition %r. Error is :\n%r' %
                  (computer_partition.getId(), server_error.args[0]))

    logger.info("Finished usage reports.")

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    return SLAPGRID_SUCCESS
