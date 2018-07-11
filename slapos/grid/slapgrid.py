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
import logging
import json
import shutil

if sys.version_info < (2, 6):
  warnings.warn('Used python version (%s) is old and has problems with'
      ' IPv6 connections' % sys.version.split('\n')[0])

from lxml import etree

from slapos import manager as slapmanager
from slapos.slap.slap import NotFoundError
from slapos.slap.slap import ServerError
from slapos.slap.slap import COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME
from slapos.util import mkdir_p, chownDirectory, string_to_boolean
from slapos.grid.exception import BuildoutFailedError
from slapos.grid.SlapObject import Software, Partition
from slapos.grid.svcbackend import (launchSupervisord,
                                    createSupervisordConfiguration,
                                    _getSupervisordConfigurationDirectory,
                                    _getSupervisordSocketPath)
from slapos.grid.utils import (md5digest, dropPrivileges, SlapPopen, updateFile)
from slapos.grid.promise import PromiseLauncher, PromiseError
from slapos.grid.promise.generic import PROMISE_LOG_FOLDER_NAME
from slapos.human import human2bytes
import slapos.slap
from netaddr import valid_ipv4, valid_ipv6


# XXX: should be moved to SLAP library
COMPUTER_PARTITION_DESTROYED_STATE = 'destroyed'
COMPUTER_PARTITION_STARTED_STATE = 'started'
COMPUTER_PARTITION_STOPPED_STATE = 'stopped'

# Global variables about return state of slapgrid
SLAPGRID_SUCCESS = 0
SLAPGRID_FAIL = 1
SLAPGRID_PROMISE_FAIL = 2
PROMISE_TIMEOUT = 3

COMPUTER_PARTITION_TIMESTAMP_FILENAME = '.timestamp'
COMPUTER_PARTITION_LATEST_BANG_TIMESTAMP_FILENAME = '.slapos_latest_bang_timestamp'
COMPUTER_PARTITION_INSTALL_ERROR_FILENAME = '.slapgrid-%s-error.log'
COMPUTER_PARTITION_WAIT_LIST_FILENAME = '.slapos-report-wait-service-list'

# XXX hardcoded watchdog_path
WATCHDOG_PATH = '/opt/slapos/bin/slapos-watchdog'


class _formatXMLError(Exception):
  pass


class FPopen(subprocess.Popen):
  def __init__(self, *args, **kwargs):
    kwargs['stdin'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    kwargs.setdefault('stdout', subprocess.PIPE)
    kwargs.setdefault('close_fds', True)
    kwargs.setdefault('shell', True)
    subprocess.Popen.__init__(self, *args, **kwargs)
    self.stdin.flush()
    self.stdin.close()
    self.stdin = None

def check_missing_parameters(options):
  required = set([
      'computer_id',
      # XXX: instance_root is better named "partition_root"
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

  # parameter can NOT be empty string or None
  for option in required:
    if not options.get(option):
      missing.add(option)

  if missing:
    raise RuntimeError('Mandatory parameters present but empty: %s' % ', '.join(sorted(missing)))


def check_missing_files(options):
  req_files = [
      options.get('key_file'),
      options.get('cert_file'),
      options.get('master_ca_file'),
      options.get('shacache-ca-file'),
      options.get('shacache-cert-file'),
      options.get('shacache-key-file'),
      options.get('shadir-ca-file'),
      options.get('shadir-cert-file'),
      options.get('shadir-key-file'),
      options.get('signature-private-key-file',
        options.get('signature_private_key_file')),
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


def merged_options(args, configp):
  options = dict(configp.items('slapos'))

  if configp.has_section('networkcache'):
    options.update(dict(configp.items('networkcache')))
  for key, value in vars(args).iteritems():
    if value is not None:
      options[key] = value

  if options.get('all'):
    options['develop'] = True

  # Parse cache / binary cache options
  # Backward compatibility about "binary-cache-url-blacklist" deprecated option
  if (options.get("binary-cache-url-blacklist") and not
        options.get("download-from-binary-cache-url-blacklist")):
    options["download-from-binary-cache-url-blacklist"] = \
        options["binary-cache-url-blacklist"]
  options["download-from-binary-cache-url-blacklist"] = [
      url.strip() for url in options.get(
          "download-from-binary-cache-url-blacklist", "").split('\n') if url]
  options["upload-to-binary-cache-url-blacklist"] = [
      url.strip() for url in options.get(
          "upload-to-binary-cache-url-blacklist", "").split('\n') if url]

  options['firewall'] = {}
  if configp.has_section('firewall'):
    options['firewall'] = dict(configp.items('firewall'))
    options['firewall']["authorized_sources"] = [
        source.strip() for source in options['firewall'].get(
            "authorized_sources", "").split('\n') if source]
    options['firewall']['firewall_cmd'] = options['firewall'].get(
            "firewall_cmd", "firewall-cmd")
    options['firewall']['firewall_executable'] = options['firewall'].get(
            "firewall_executable", "")
    options['firewall']['dbus_executable'] = options['firewall'].get(
            "dbus_executable", "")
    options['firewall']['reload_config_cmd'] = options['firewall'].get(
            "reload_config_cmd",
            "slapos node restart firewall")

  return options


def random_delay(options, logger):
  """
  Sleep for a random time to avoid SlapOS Master being DDOSed by an army of
  SlapOS Nodes configured with cron.
  """
  if options['now']:
    # XXX-Cedric: deprecate '--now'
    return

  maximal_delay = int(options.get('maximal_delay', '0'))
  if maximal_delay:
    duration = random.randint(1, maximal_delay)
    logger.info('Sleeping for %s seconds. To disable this feature, '
                'check --now parameter in slapgrid help.', duration)
    time.sleep(duration)


def create_slapgrid_object(options, logger):
  signature_certificate_list = None
  if 'signature-certificate-list' in options:
    cert_marker = '-----BEGIN CERTIFICATE-----'
    signature_certificate_list = [
        cert_marker + '\n' + q.strip()
        for q in options['signature-certificate-list'].split(cert_marker)
        if q.strip()
    ]

  op = options
  software_min_free_space = human2bytes(op.get('software_min_free_space', '1000M'))
  instance_min_free_space = human2bytes(op.get('instance_min_free_space', '1000M'))

  return Slapgrid(software_root=op['software_root'],
                  instance_root=op['instance_root'],
                  master_url=op['master_url'],
                  computer_id=op['computer_id'],
                  buildout=op.get('buildout'),
                  logger=logger,
                  maximum_periodicity = op.get('maximum_periodicity', 86400),
                  key_file=op.get('key_file'),
                  cert_file=op.get('cert_file'),
                  signature_private_key_file=op.get(
                    'signature-private-key-file', op.get('signature_private_key_file')),
                  signature_certificate_list=signature_certificate_list,
                  download_binary_cache_url=op.get('download-binary-cache-url'),
                  upload_binary_cache_url=op.get('upload-binary-cache-url'),
                  download_from_binary_cache_url_blacklist=
                      op.get('download-from-binary-cache-url-blacklist', []),
                  upload_to_binary_cache_url_blacklist=
                      op.get('upload-to-binary-cache-url-blacklist', []),
                  upload_cache_url=op.get('upload-cache-url'),
                  download_binary_dir_url=op.get('download-binary-dir-url'),
                  upload_binary_dir_url=op.get('upload-binary-dir-url'),
                  upload_dir_url=op.get('upload-dir-url'),
                  master_ca_file=op.get('master_ca_file'),
                  certificate_repository_path=op.get('certificate_repository_path'),
                  promise_timeout=op.get('promise_timeout', PROMISE_TIMEOUT),
                  shacache_ca_file=op.get('shacache-ca-file'),
                  shacache_cert_file=op.get('shacache-cert-file'),
                  shacache_key_file=op.get('shacache-key-file'),
                  shadir_ca_file=op.get('shadir-ca-file'),
                  shadir_cert_file=op.get('shadir-cert-file'),
                  shadir_key_file=op.get('shadir-key-file'),
                  forbid_supervisord_automatic_launch=string_to_boolean(op.get('forbid_supervisord_automatic_launch', 'false')),
                  develop=op.get('develop', False),
                  # Try to fetch from deprecated argument
                  software_release_filter_list=op.get('only-sr', op.get('only_sr')),
                  # Try to fetch from deprecated argument
                  computer_partition_filter_list=op.get('only-cp', op.get('only_cp')),
                  software_min_free_space=software_min_free_space,
                  instance_min_free_space=instance_min_free_space,
                  instance_storage_home=op.get('instance_storage_home'),
                  ipv4_global_network=op.get('ipv4_global_network'),
                  firewall_conf=op.get('firewall'),
                  config=options)


def check_required_only_partitions(existing, required):
  """
  Verify the existence of partitions specified by the --only parameter
  """
  missing = set(required) - set(existing)
  if missing:
    plural = ['s', ''][len(missing) == 1]
    raise ValueError('Unknown partition%s: %s' % (plural, ', '.join(sorted(missing))))


class Slapgrid(object):
  """ Main class for SlapGrid. Fetches and processes informations from master
  server and pushes usage information to master server.
  """

  def __init__(self,
               software_root,
               instance_root,
               master_url,
               computer_id,
               buildout,
               logger,
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
               shacache_ca_file=None,
               shacache_cert_file=None,
               shacache_key_file=None,
               shadir_ca_file=None,
               shadir_cert_file=None,
               shadir_key_file=None,
               forbid_supervisord_automatic_launch=False,
               develop=False,
               software_release_filter_list=None,
               computer_partition_filter_list=None,
               software_min_free_space=None,
               instance_min_free_space=None,
               instance_storage_home=None,
               ipv4_global_network=None,
               firewall_conf={},
               config=None,
               ):
    """Makes easy initialisation of class parameters"""
    # Parses arguments
    self.software_root = os.path.abspath(software_root)
    self.instance_root = os.path.abspath(instance_root)
    self.master_url = master_url
    self.computer_id = computer_id
    self.supervisord_socket = _getSupervisordSocketPath(instance_root)
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
    self.shacache_ca_file = shacache_ca_file
    self.shacache_cert_file = shacache_cert_file
    self.shacache_key_file = shacache_key_file
    self.shadir_ca_file = shadir_ca_file
    self.shadir_cert_file = shadir_cert_file
    self.shadir_key_file = shadir_key_file
    self.forbid_supervisord_automatic_launch = forbid_supervisord_automatic_launch
    self.logger = logger
    # Creates objects from slap module
    self.slap = slapos.slap.slap()
    self.slap.initializeConnection(self.master_url, key_file=self.key_file,
        cert_file=self.cert_file, master_ca_file=self.master_ca_file)
    self.computer = self.slap.registerComputer(self.computer_id)
    # Defines all needed paths
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
    self.software_min_free_space = software_min_free_space
    self.instance_min_free_space = instance_min_free_space
    if instance_storage_home:
      self.instance_storage_home = os.path.abspath(instance_storage_home)
    else:
      self.instance_storage_home = ""
    if ipv4_global_network:
      self.ipv4_global_network = ipv4_global_network
    else:
      self.ipv4_global_network= ""
    self.firewall_conf = firewall_conf
    self.config = config
    self._manager_list = slapmanager.from_config(config)

  def _getWatchdogLine(self):
    invocation_list = [WATCHDOG_PATH]
    invocation_list.append("--master-url '%s' " % self.master_url)
    if self.certificate_repository_path:
      invocation_list.append("--certificate-repository-path '%s'" %
                                self.certificate_repository_path)
    invocation_list.append("--computer-id '%s'" % self.computer_id)
    invocation_list.append("--instance-root '%s'" % self.instance_root)
    return ' '.join(invocation_list)

  def _generateFirewallSupervisorConf(self):
    """If firewall section is defined in slapos configuration, generate
      supervisor configuration entry for firewall process.
    """
    supervisord_conf_folder_path = os.path.join(self.instance_root,
                                               'etc', 'supervisord.conf.d')
    supervisord_firewall_conf = os.path.join(supervisord_conf_folder_path,
                                              'firewall.conf')
    if not self.firewall_conf or not self.firewall_conf.get('firewall_executable') \
      or self.firewall_conf.get('testing', False):
      if os.path.exists(supervisord_firewall_conf):
        os.unlink(supervisord_firewall_conf)
      return
    supervisord_firewall_program_conf = """\
[program:firewall]
directory=/opt/slapos
command=%(firewall_executable)s
process_name=firewall
priority=5
autostart=true
autorestart=true
startsecs=0
startretries=0
exitcodes=0
stopsignal=TERM
stopwaitsecs=60
user=0
group=0
serverurl=AUTO
redirect_stderr=true
stdout_logfile=%(log_file)s
stdout_logfile_maxbytes=100KB
stdout_logfile_backups=1
stderr_logfile=%(log_file)s
stderr_logfile_maxbytes=100KB
stderr_logfile_backups=1
""" %  {'firewall_executable': self.firewall_conf['firewall_executable'],
        'log_file': self.firewall_conf.get('log_file', '/var/log/firewall.log')}

    if not os.path.exists(supervisord_conf_folder_path):
      os.makedirs(supervisord_conf_folder_path)
    updateFile(supervisord_firewall_conf, supervisord_firewall_program_conf)


  def _generateDbusSupervisorConf(self):
    """If dbus command is defined in slapos configuration, generate
      supervisor configuration entry for dbus daemon.
    """
    supervisord_conf_folder_path = os.path.join(self.instance_root,
                                               'etc', 'supervisord.conf.d')
    supervisord_dbus_conf = os.path.join(supervisord_conf_folder_path,
                                              'dbus.conf')
    if not self.firewall_conf or not self.firewall_conf.get('dbus_executable') \
      or self.firewall_conf.get('testing', False):
      if os.path.exists(supervisord_dbus_conf):
        os.unlink(supervisord_dbus_conf)
      return
    supervisord_dbus_program_conf = """\
[program:dbus]
directory=/opt/slapos
command=%(dbus_executable)s
process_name=dbus
priority=1
autostart=true
autorestart=true
startsecs=0
startretries=0
exitcodes=0
stopsignal=TERM
stopwaitsecs=60
user=0
group=0
serverurl=AUTO
redirect_stderr=true
stdout_logfile=%(dbus_log_file)s
stdout_logfile_maxbytes=100KB
stdout_logfile_backups=1
stderr_logfile=%(dbus_log_file)s
stderr_logfile_maxbytes=100KB
stderr_logfile_backups=1
""" %  {'dbus_executable': self.firewall_conf['dbus_executable'],
        'dbus_log_file': self.firewall_conf.get('dbus_log_file', '/var/log/dbus.log')}

    if not os.path.exists(supervisord_conf_folder_path):
      os.makedirs(supervisord_conf_folder_path)
    updateFile(supervisord_dbus_conf, supervisord_dbus_program_conf)

  def checkEnvironmentAndCreateStructure(self):
    """Checks for software_root and instance_root existence, then creates
       needed files and directories.
    """
    # Checks for software_root and instance_root existence
    if not os.path.isdir(self.software_root):
      raise OSError('%s does not exist.' % self.software_root)

    createSupervisordConfiguration(self.instance_root, self._getWatchdogLine())
    self._generateFirewallSupervisorConf()
    self._generateDbusSupervisorConf()

  def _launchSupervisord(self):
    if not self.forbid_supervisord_automatic_launch:
      launchSupervisord(instance_root=self.instance_root, logger=self.logger)

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
    self.logger.info('Processing software releases...')
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
            logger=self.logger,
            signature_private_key_file=self.signature_private_key_file,
            signature_certificate_list=self.signature_certificate_list,
            download_binary_cache_url=self.download_binary_cache_url,
            upload_binary_cache_url=self.upload_binary_cache_url,
            download_from_binary_cache_url_blacklist=
                self.download_from_binary_cache_url_blacklist,
            upload_to_binary_cache_url_blacklist=
                self.upload_to_binary_cache_url_blacklist,
            upload_cache_url=self.upload_cache_url,
            download_binary_dir_url=self.download_binary_dir_url,
            upload_binary_dir_url=self.upload_binary_dir_url,
            upload_dir_url=self.upload_dir_url,
            shacache_ca_file=self.shacache_ca_file,
            shacache_cert_file=self.shacache_cert_file,
            shacache_key_file=self.shacache_key_file,
            shadir_ca_file=self.shadir_ca_file,
            shadir_cert_file=self.shadir_cert_file,
            shadir_key_file=self.shadir_key_file,
            software_min_free_space=self.software_min_free_space)

        # call manager for every software release
        for manager in self._manager_list:
          manager.software(software)

        if state == 'available':
          completed_tag = os.path.join(software_path, '.completed')
          if (self.develop or (not os.path.exists(completed_tag) and
                 len(self.software_release_filter_list) == 0) or
                 url_hash in self.software_release_filter_list or
                 url_hash in (md5digest(uri) for uri in self.software_release_filter_list)):
            try:
              software_release.building()
            except NotFoundError:
              pass
            software.install()
            with open(completed_tag, 'w') as fout:
              fout.write(time.asctime())
        elif state == 'destroyed':
          if os.path.exists(software_path):
            self.logger.info('Destroying %r...' % software_release_uri)
            software.destroy()
            self.logger.info('Destroyed %r.' % software_release_uri)

        # call manager for every software release
        for manager in self._manager_list:
          manager.softwareTearDown(software)
      # Send log before exiting
      except (SystemExit, KeyboardInterrupt):
        software_release.error(traceback.format_exc(), logger=self.logger)
        raise

      # Buildout failed: send log but don't print it to output (already done)
      except BuildoutFailedError as exc:
        clean_run = False
        try:
          software_release.error(exc, logger=self.logger)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          self.logger.exception('Problem while reporting error, continuing:')

      # For everything else: log it, send it, continue.
      except Exception:
        self.logger.exception('')
        software_release.error(traceback.format_exc(), logger=self.logger)
        clean_run = False
      else:
        if state == 'available':
          try:
            software_release.available()
          except (NotFoundError, ServerError):
            pass
        elif state == 'destroyed':
          try:
            software_release.destroyed()
          except (NotFoundError, ServerError):
            self.logger.exception('')
    self.logger.info('Finished software releases.')

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    return SLAPGRID_SUCCESS

  def _checkPromiseList(self, partition, force=True, check_anomaly=False):
    instance_path = os.path.join(self.instance_root, partition.partition_id)
    promise_log_path = os.path.join(instance_path, PROMISE_LOG_FOLDER_NAME)

    self.logger.info("Checking %s promises..." % partition.partition_id)
    uid, gid = None, None
    stat_info = os.stat(instance_path)

    #stat sys call to get statistics informations
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    promise_dir = os.path.join(instance_path, 'etc', 'plugin')
    legacy_promise_dir = os.path.join(instance_path, 'etc', 'promise')
    promise_config = {
      'promise-folder': promise_dir,
      'legacy-promise-folder': legacy_promise_dir,
      'promise-timeout': self.promise_timeout,
      'uid': uid,
      'gid': gid,
      'partition-folder': instance_path,
      'log-folder': promise_log_path,
      'force': force,
      'check-anomaly': check_anomaly,
      'master-url': partition.server_url,
      'partition-cert': partition.cert_file,
      'partition-key': partition.key_file,
      'partition-id': partition.partition_id,
      'computer-id': self.computer_id,
    }

    promise_checker = PromiseLauncher(config=promise_config, logger=self.logger)
    return promise_checker.run()

  def _endInstallationTransaction(self, computer_partition):
    partition_id = computer_partition.getId()
    transaction_file_name = COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME % partition_id
    transaction_file_path = os.path.join(self.instance_root,
                                      partition_id,
                                      transaction_file_name)

    if os.path.exists(transaction_file_path):
      with open(transaction_file_path, 'r') as tf:
        try:
          computer_partition.setComputerPartitionRelatedInstanceList(
            [reference for reference in tf.read().split('\n') if reference]
          )
        except NotFoundError, e:
          # Master doesn't implement this feature ?
          self.logger.warning("NotFoundError: %s. \nCannot send requested instance "\
                            "list to master. Please check if this feature is"\
                            "implemented on SlapOS Master." % str(e))

  def _addFirewallRule(self, rule_command):
    """
    """
    query_cmd = rule_command.replace('--add-rule', '--query-rule')
    process = FPopen(query_cmd)
    result, stderr = process.communicate()
    if result.strip() == 'no':
      # rule doesn't exist add to firewall
      self.logger.debug(rule_command)
      process = FPopen(rule_command)
      rule_result, stderr = process.communicate()
      if process.returncode == 0:
        if rule_result.strip() != 'success':
          raise Exception(rule_result)
      else:
        raise Exception("Failed to add firewalld rule %s\n%s.\n%s" % (
                        rule_command, rule_result, stderr))
    elif result.strip() != 'no' and process.returncode != 0:
      raise Exception("Failed to run firewalld rule %s\n%s.\n%s" % (
                      query_cmd, result, stderr))

    return result.strip() == 'no'

  def _removeFirewallRule(self, rule_command):
    """
    """
    query_cmd = rule_command.replace('--add-rule', '--query-rule')
    process = FPopen(query_cmd)
    result, stderr = process.communicate()
    if result.strip() == 'yes':
      # The rule really exist, remove it
      remove_command = rule_command.replace('--add-rule', '--remove-rule')
      self.logger.debug(remove_command)
      process = FPopen(remove_command)
      rule_result, stderr = process.communicate()
      if process.returncode == 0:
        if rule_result.strip() != 'success':
          raise Exception(rule_result)
      else:
        raise Exception("Failed to add firewalld rule %s\n%s.\n%s" % (
                        rule_command, rule_result, stderr))
    elif result.strip() != 'no' and process.returncode != 0:
      raise Exception("Failed to run firewalld rule %s\n%s.\n%s" % (
                      query_cmd, result, stderr))

    return result.strip() == 'yes'

  def _checkAddFirewallRules(self, partition_id, command_list, add=True):
    """
    Process Firewall rules from and save rules to firewall_rules_path
    """
    
    instance_path = os.path.join(self.instance_root, partition_id)
    firewall_rules_path = os.path.join(instance_path,
                                Partition.partition_firewall_rules_name)
    reload_rules = False
    fw_base_cmd = self.firewall_conf['firewall_cmd']
    json_list = []

    if os.path.exists(firewall_rules_path):
      with open(firewall_rules_path, 'r') as frules:
        rules_list = json.loads(frules.read())

      for command in rules_list:
        skip_remove = False
        if add:
          for new_cmd in command_list:
            if command == new_cmd:
              skip_remove = True
              break

        if not skip_remove:
          state = self._removeFirewallRule('%s %s' % (fw_base_cmd, command))
          reload_rules = reload_rules or state

    if add:
      json_list = command_list
      for command in command_list:
        state = self._addFirewallRule('%s %s' % (fw_base_cmd, command))
        reload_rules = reload_rules or state

    if reload_rules:
      # Apply changes: reload configuration
      # XXX - need to check firewalld reload instead of restart
      self.logger.info("Reloading firewall configuration...")
      reload_cmd = self.firewall_conf['reload_config_cmd']
      reload_process = FPopen(reload_cmd)
      stdout, stderr = reload_process.communicate()
      if reload_process.returncode != 0:
        raise Exception("Failed to load firewalld rules with command %s.\n%" % (
                        stderr, reload_cmd))

      with open(firewall_rules_path, 'w') as frules:
        frules.write(json.dumps(json_list))

  def _getFirewallAcceptRules(self, ip, hosting_ip_list, source_ip_list, ip_type='ipv4'):
    """
    Generate rules for firewall based on list of IP that should have access to `ip`
    """
    if ip_type not in ['ipv4', 'ipv6', 'eb']:
      raise NotImplementedError("firewall-cmd has not rules with tables %s." % ip_type)

    command = '--permanent --direct --add-rule %s filter' % ip_type

    cmd_list = []
    ip_list = hosting_ip_list + source_ip_list

    for other_ip in ip_list:
      # Configure INPUT rules
      cmd_list.append('%s INPUT 0 -s %s -d %s -j ACCEPT' % (command,
                                                            other_ip, ip))
      # Configure FORWARD rules
      cmd_list.append('%s FORWARD 0 -s %s -d %s -j ACCEPT' % (command,
                                                              other_ip, ip))

    # Reject all other requests
    cmd_list.append('%s INPUT 1000 -d %s -j REJECT' % (command, ip))
    cmd_list.append('%s FORWARD 1000 -d %s -j REJECT' % (command, ip))
    cmd_list.append('%s INPUT 900 -d %s -m state --state ESTABLISHED,RELATED -j REJECT' % (
                    command, ip))
    cmd_list.append('%s FORWARD 900 -d %s -m state --state ESTABLISHED,RELATED -j REJECT' % (
                    command, ip))

    return cmd_list

  def _getFirewallRejectRules(self, ip, hosting_ip_list, source_ip_list, ip_type='ipv4'):
    """
    Generate rules for firewall based on list of IP that should not have access to `ip`
    """
    if ip_type not in ['ipv4', 'ipv6', 'eb']:
      raise NotImplementedError("firewall-cmd has not rules with tables %s." % ip_type)

    command = '--permanent --direct --add-rule %s filter' % ip_type

    cmd_list = []

    # Accept all other requests
    #cmd_list.append('%s INPUT 1000 -d %s -j ACCEPT' % (command, ip))
    #cmd_list.append('%s FORWARD 1000 -d %s -j ACCEPT' % (command, ip))

    # Reject all other requests from the list
    for other_ip in source_ip_list:
      cmd_list.append('%s INPUT 800 -s %s -d %s -m state --state ESTABLISHED,RELATED -j REJECT' % (
                    command, other_ip, ip))
      cmd_list.append('%s FORWARD 800 -s %s -d %s -m state --state ESTABLISHED,RELATED -j REJECT' % (
                    command, other_ip, ip))
      cmd_list.append('%s INPUT 900 -s %s -d %s -j REJECT' % (command,
                                                            other_ip, ip))
      cmd_list.append('%s FORWARD 900 -s %s -d %s -j REJECT' % (command,
                                                              other_ip, ip))
    # Accept on this hosting subscription
    for other_ip in hosting_ip_list:
      cmd_list.append('%s INPUT 0 -s %s -d %s -j ACCEPT' % (command,
                                                            other_ip, ip))
      cmd_list.append('%s FORWARD 0 -s %s -d %s -j ACCEPT' % (command,
                                                              other_ip, ip))

    return cmd_list

  def _getValidIpv4FromList(self, ipv4_list, warn=False):
    """
    Return the list containing only valid ipv4 or network address.
    """
    valid_list = []
    for ip in ipv4_list:
      if not ip:
        continue
      the_ip = ip.split('/')[0]
      if valid_ipv4(the_ip):
        valid_list.append(ip)
      elif warn:
        self.logger.warn("IP/Network address %s is not valid. ignored.." % ip)
    return valid_list

  def _setupComputerPartitionFirewall(self, computer_partition, ip_list, drop_entries=False):
    """
    Using linux iptables, limit access to IP of this partition to all 
    others partitions of the same Hosting Subscription
    """
    ipv4_list = []
    ipv6_list = []
    source_ipv4_list = []
    source_ipv6_list = []
    hosting_ipv4_list = []
    hosting_ipv6_list = []
    getFirewallRules = getattr(self, '_getFirewallAcceptRules')

    if not drop_entries:
      self.logger.info("Configuring firewall...")
      add_rules = True
    else:
      add_rules = False
      self.logger.info("Removing firewall configuration...")

    for net_ip in ip_list:
      iface, ip = (net_ip[0], net_ip[1])
      if not iface.startswith('route_'):
        continue
      if valid_ipv4(ip):
        ipv4_list.append(ip)
      elif valid_ipv6(ip):
        ipv6_list.append(ip)

    hosting_ip_list = computer_partition.getFullHostingIpAddressList()
    for iface, ip in hosting_ip_list:
      if valid_ipv4(ip):
        if not ip in ipv4_list:
          hosting_ipv4_list.append(ip)
      elif valid_ipv6(ip):
        if not ip in ipv6_list:
          hosting_ipv6_list.append(ip)

    filter_dict = getattr(computer_partition, '_filter_dict', None)
    extra_list = []
    accept_ip_list = []
    if filter_dict is not None:
      if filter_dict.get('fw_restricted_access', 'on') == 'off':
        extra_list = filter_dict.get('fw_rejected_sources', '').split(' ')
        getFirewallRules = getattr(self, '_getFirewallRejectRules')
        accept_ip_list.extend(self.firewall_conf.get('authorized_sources', []))
        accept_ip_list.extend(filter_dict.get('fw_authorized_sources', '').split(' '))
      else:
        extra_list = filter_dict.get('fw_authorized_sources', '').split(' ')
        extra_list.extend(self.firewall_conf.get('authorized_sources', []))

    source_ipv4_list = self._getValidIpv4FromList(extra_list, True)
    hosting_ipv4_list.extend(self._getValidIpv4FromList(accept_ip_list, True))

    # XXX - ipv6_list and source_ipv6_list ignored for the moment
    for ip in ipv4_list:
      cmd_list = getFirewallRules(ip, hosting_ipv4_list,
                                  source_ipv4_list, ip_type='ipv4')
      self._checkAddFirewallRules(computer_partition.getId(),
                                  cmd_list, add=add_rules)

  def _checkPromiseAnomaly(self, local_partition, computer_partition):
    partition_access_status = computer_partition.getAccessStatus()
    status_error = False
    if partition_access_status and partition_access_status.startswith("#error"):
      status_error = True
    try:
      self._checkPromiseList(local_partition,
                             check_anomaly=True,
                             force=False)
    except PromiseError, e:
      self.logger.error(e)
      if partition_access_status is None or not status_error:
        computer_partition.error(e, logger=self.logger)
    else:
      if partition_access_status is None or status_error:
        computer_partition.started()

  def processComputerPartition(self, computer_partition):
    """
    Process a Computer Partition, depending on its state
    """
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

    self.logger.debug('Check if %s requires processing...' % computer_partition_id)

    instance_path = os.path.join(self.instance_root, computer_partition_id)
    os.environ['SLAPGRID_INSTANCE_ROOT'] = self.instance_root

    # Check if transaction file of this partition exists, if the file was created,
    # remove it so it will be generate with this new transaction
    transaction_file_name = COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME % computer_partition_id
    transaction_file_path = os.path.join(instance_path, transaction_file_name)
    if os.path.exists(transaction_file_path):
      os.unlink(transaction_file_path)

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

    error_output_file = os.path.join(
        instance_path,
        COMPUTER_PARTITION_INSTALL_ERROR_FILENAME % computer_partition_id
    )

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

    computer_partition_state = computer_partition.getState()
    periodicity = self.maximum_periodicity
    if software_path:
      periodicity_path = os.path.join(software_path, 'periodicity')
      if os.path.exists(periodicity_path):
        try:
          periodicity = int(open(periodicity_path).read())
        except ValueError:
          os.remove(periodicity_path)
          self.logger.exception('')

    local_partition = Partition(
      software_path=software_path,
      instance_path=instance_path,
      supervisord_partition_configuration_path=os.path.join(
        _getSupervisordConfigurationDirectory(self.instance_root), '%s.conf' %
        computer_partition_id),
      supervisord_socket=self.supervisord_socket,
      computer_partition=computer_partition,
      computer_id=self.computer_id,
      partition_id=computer_partition_id,
      server_url=self.master_url,
      software_release_url=software_url,
      certificate_repository_path=self.certificate_repository_path,
      buildout=self.buildout,
      logger=self.logger,
      retention_delay=getattr(computer_partition, '_filter_dict', {}).get('retention_delay', '0'),
      instance_min_free_space=self.instance_min_free_space,
      instance_storage_home=self.instance_storage_home,
      ipv4_global_network=self.ipv4_global_network,
    )

    # let managers modify current partition
    for manager in self._manager_list:
      manager.instance(local_partition)

    # Check if timestamp from server is more recent than local one.
    # If not: it's not worth processing this partition (nothing has
    # changed).
    if (computer_partition_id not in self.computer_partition_filter_list and
          not self.develop and os.path.exists(timestamp_path)):
      old_timestamp = open(timestamp_path).read()
      last_runtime = int(os.path.getmtime(timestamp_path))
      if timestamp:
        try:
          if periodicity == 0:
            os.remove(timestamp_path)
          elif int(timestamp) <= int(old_timestamp):
            # Check periodicity, i.e if periodicity is one day, partition
            # should be processed at least every day.
            if int(time.time()) <= (last_runtime + periodicity) or periodicity < 0:
              # check promises anomaly
              if computer_partition_state == COMPUTER_PARTITION_STARTED_STATE:
                self.logger.debug('Partition already up-to-date.')
                self._checkPromiseAnomaly(local_partition, computer_partition)
              else:
                self.logger.debug('Partition already up-to-date. skipping.')

              # Run manager tear down
              for manager in self._manager_list:
                manager.instanceTearDown(local_partition)

              return
            else:
              # Periodicity forced processing this partition. Removing
              # the timestamp file in case it fails.
              os.remove(timestamp_path)
        except ValueError:
          os.remove(timestamp_path)
          self.logger.exception('')

    # Include Partition Logging
    log_folder_path = "%s/.slapgrid/log" % instance_path
    mkdir_p(log_folder_path)
    partition_file_handler = logging.FileHandler(
                filename="%s/instance.log" % (log_folder_path)
            )
    stat_info = os.stat(instance_path)
    chownDirectory("%s/.slapgrid" % instance_path,
                   uid=stat_info.st_uid,
                   gid=stat_info.st_gid)

    formatter = logging.Formatter(
       '[%(asctime)s] %(levelname)-8s %(name)s %(message)s')
    partition_file_handler.setFormatter(formatter)
    self.logger.addHandler(partition_file_handler)

    try:
      self.logger.info('Processing Computer Partition %s.' % computer_partition_id)
      self.logger.info('  Software URL: %s' % software_url)
      self.logger.info('  Software path: %s' % software_path)
      self.logger.info('  Instance path: %s' % instance_path)

      # XXX this line breaks 37 tests
      # self.logger.info('  Instance type: %s' % computer_partition.getType())
      self.logger.info('  Instance status: %s' % computer_partition_state)

      if os.path.exists(error_output_file):
        os.unlink(error_output_file)

      partition_ip_list = full_hosting_ip_list = []
      if self.firewall_conf:
        partition_ip_list = parameter_dict['ip_list'] + parameter_dict.get(
                                                            'full_ip_list', [])

      if computer_partition_state == COMPUTER_PARTITION_STARTED_STATE:
        local_partition.install()
        local_partition.start()
        if self.firewall_conf:
          self._setupComputerPartitionFirewall(computer_partition,
                                              partition_ip_list)
        self._checkPromiseList(local_partition)
        computer_partition.started()
        self._endInstallationTransaction(computer_partition)
      elif computer_partition_state == COMPUTER_PARTITION_STOPPED_STATE:
        try:
          # We want to process the partition, even if stopped, because it should
          # propagate the state to children if any.
          local_partition.install()
          if self.firewall_conf:
            self._setupComputerPartitionFirewall(computer_partition,
                                                partition_ip_list)
        finally:
          # Instance has to be stopped even if buildout/reporting is wrong.
          local_partition.stop()
        try:
          computer_partition.stopped()
        except (SystemExit, KeyboardInterrupt):
          computer_partition.error(traceback.format_exc(), logger=self.logger)
          raise
        except Exception:
          pass
        self._endInstallationTransaction(computer_partition)
      elif computer_partition_state == COMPUTER_PARTITION_DESTROYED_STATE:
        local_partition.stop()
        if self.firewall_conf:
          self._setupComputerPartitionFirewall(computer_partition,
                                              partition_ip_list,
                                              drop_entries=True)
        try:
          computer_partition.stopped()
        except (SystemExit, KeyboardInterrupt):
          computer_partition.error(traceback.format_exc(), logger=self.logger)
          raise
        except Exception:
          pass
      else:
        error_string = "Computer Partition %r has unsupported state: %s" % \
          (computer_partition_id, computer_partition_state)
        computer_partition.error(error_string, logger=self.logger)
        raise NotImplementedError(error_string)
    except Exception, e:
      if not isinstance(e, PromiseError):
        with open(error_output_file, 'w') as error_file:
          # Write error message in a log file assible to computer partition user
          error_file.write(str(e))
        if computer_partition_state == COMPUTER_PARTITION_STARTED_STATE:
          try:
            self._checkPromiseList(local_partition)
          except PromiseError:
            # updating promises state, no need to raise here
            pass
      raise e
    else:
      self.logger.removeHandler(partition_file_handler)

    # Run manager tear down
    for manager in self._manager_list:
      manager.instanceTearDown(local_partition)

    # If partition has been successfully processed, write timestamp
    if timestamp:
      open(timestamp_path, 'w').write(timestamp)

  def FilterComputerPartitionList(self, computer_partition_list):
    """
    Try to filter valid partitions to be processed from free partitions.
    """
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
           not software_url:
          # Exclude files which may come from concurrent processing 
          #  ie.: slapos ndoe report and slapos node instance commands 
          # can create a .timestamp file.
          file_list = os.listdir(computer_partition_path)
          for garbage_file in [".slapgrid", ".timestamp"]:
            if garbage_file in file_list:
              garbage_path = "/".join([computer_partition_path, garbage_file])
              if os.path.isfile(garbage_path):
                os.unlink(garbage_path)
              else:
                shutil.rmtree(garbage_path)

          if os.listdir(computer_partition_path) != []:
            self.logger.warning("Free partition %s contains file(s) in %s." % (
                computer_partition.getId(), computer_partition_path))
          continue

        # Everything seems fine
        filtered_computer_partition_list.append(computer_partition)

      # XXX-Cedric: factor all this error handling

      # Send log before exiting
      except (SystemExit, KeyboardInterrupt):
        computer_partition.error(traceback.format_exc(), logger=self.logger)
        raise

      except Exception as exc:
        # if Buildout failed: send log but don't print it to output (already done)
        if not isinstance(exc, BuildoutFailedError):
          # For everything else: log it, send it, continue.
          self.logger.exception('')
        try:
          computer_partition.error(exc, logger=self.logger)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          self.logger.exception('Problem while reporting error, continuing:')

    return filtered_computer_partition_list

  def processComputerPartitionList(self):
    """
    Will start supervisord and process each Computer Partition.
    """
    self.logger.info('Processing computer partitions...')
    # Prepares environment
    self.checkEnvironmentAndCreateStructure()
    self._launchSupervisord()

    # Boolean to know if every instance has correctly been deployed
    clean_run = True
    # Boolean to know if every promises correctly passed
    clean_run_promise = True

    check_required_only_partitions([cp.getId() for cp in self.getComputerPartitionList()],
                                   self.computer_partition_filter_list)

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
        computer_partition.error(traceback.format_exc(), logger=self.logger)
        raise

      except PromiseError as exc:
        clean_run_promise = False
        try:
          self.logger.error(exc)
          computer_partition.error(exc, logger=self.logger)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          self.logger.exception('Problem while reporting error, continuing:')

      except Exception as exc:
        clean_run = False
        # if Buildout failed: send log but don't print it to output (already done)
        if not isinstance(exc, BuildoutFailedError):
          # For everything else: log it, send it, continue.
          self.logger.exception('')
        try:
          computer_partition.error(exc, logger=self.logger)
        except (SystemExit, KeyboardInterrupt):
          raise
        except Exception:
          self.logger.exception('Problem while reporting error, continuing:')

    self.logger.info('Finished computer partitions.')

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    if not clean_run_promise:
      return SLAPGRID_PROMISE_FAIL
    return SLAPGRID_SUCCESS

  def _checkWaitProcessList(self, partition, state_list):
    wait_file = os.path.join(partition.instance_path,
                             COMPUTER_PARTITION_WAIT_LIST_FILENAME)

    if os.path.exists(wait_file) and os.path.isfile(wait_file):
      with open(wait_file) as wait_f:
        processes_list = [name.strip() for name in wait_f if name]
        # return True if one of process in the list is running
        return partition.checkProcessesFromStateList(processes_list,
                                                     state_list)
    return False

  def validateXML(self, to_be_validated, xsd_model):
    """Validates a given xml file"""
    #We retrieve the xsd model
    xsd_model = StringIO.StringIO(xsd_model)
    xmlschema_doc = etree.parse(xsd_model)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    try:
      document = etree.fromstring(to_be_validated)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as exc:
      self.logger.info('Failed to parse this XML report :  %s\n%s' %
                          (to_be_validated, _formatXMLError(exc)))
      self.logger.error(_formatXMLError(exc))
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
    self.logger.info('Aggregating and sending usage reports...')

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
    # Loop over the different computer partitions
    computer_partition_list = self.FilterComputerPartitionList(
       slap_computer_usage.getComputerPartitionList())

    for computer_partition in computer_partition_list:
      try:
        computer_partition_id = computer_partition.getId()

        # We want to execute all the script in the report folder
        instance_path = os.path.join(self.instance_root,
            computer_partition.getId())
        report_path = os.path.join(instance_path, 'etc', 'report')
        if os.path.isdir(report_path):
          script_list_to_run = os.listdir(report_path)
        else:
          script_list_to_run = []

        # We now generate the pseudorandom name for the xml file
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
          # We add the xml_file name to the invocation_list
          #f = tempfile.NamedTemporaryFile()
          #name_xml = '%s.%s' % ('slapreport', os.path.basename(f.name))
          #path_to_slapreport = os.path.join(instance_path, 'var', name_xml)

          invocation_list.append(path_to_slapreport)
          # Dropping privileges
          uid, gid = None, None
          stat_info = os.stat(instance_path)
          #stat sys call to get statistics informations
          uid = stat_info.st_uid
          gid = stat_info.st_gid
          process_handler = SlapPopen(invocation_list,
                                      preexec_fn=lambda: dropPrivileges(uid, gid, logger=self.logger),
                                      cwd=os.path.join(instance_path, 'etc', 'report'),
                                      env=None,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT,
                                      logger=self.logger)
          if process_handler.returncode is None:
            process_handler.kill()
          if process_handler.returncode != 0:
            clean_run = False
            failed_script_list.append("Script %r failed." % script)
            self.logger.warning('Failed to run %r' % invocation_list)
          if len(failed_script_list):
            computer_partition.error('\n'.join(failed_script_list), logger=self.logger)
      # Whatever happens, don't stop processing other instances
      except Exception:
        self.logger.exception('Cannot run usage script(s) for %r:' %
                                  computer_partition.getId())

    # Now we loop through the different computer partitions to report
    report_usage_issue_cp_list = []
    for computer_partition in computer_partition_list:
      try:
        filename_delete_list = []
        computer_partition_id = computer_partition.getId()
        instance_path = os.path.join(self.instance_root, computer_partition_id)
        dir_report_list = [os.path.join(instance_path, 'var', 'xml_report'),
            os.path.join(self.instance_root, 'var', 'xml_report',
                         computer_partition_id)]

        for dir_reports in dir_report_list:
          # The directory xml_report contain a number of files equal
          # to the number of software instance running inside the same partition
          if os.path.isdir(dir_reports):
            filename_list = os.listdir(dir_reports)
          else:
            filename_list = []
          # self.logger.debug('name List %s' % filename_list)

          for filename in filename_list:

            file_path = os.path.join(dir_reports, filename)
            if os.path.exists(file_path):
              usage = open(file_path, 'r').read()

              # We check the validity of xml content of each reports
              if not self.validateXML(usage, partition_consumption_model):
                self.logger.info('WARNING: The XML file %s generated by slapreport is '
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
              self.logger.debug('Usage report %r not found, ignored' % file_path)

          # After sending the aggregated file we remove all the valid xml reports
          for filename in filename_delete_list:
            os.remove(os.path.join(dir_reports, filename))

      # Whatever happens, don't stop processing other instances
      except Exception:
        self.logger.exception('Cannot run usage script(s) for %r:' %
                                computer_partition.getId())

    for computer_partition_usage in computer_partition_usage_list:
      self.logger.info('computer_partition_usage_list: %s - %s' %
                       (computer_partition_usage.usage, computer_partition_usage.getId()))

    filename_delete_list = []
    computer_report_dir = os.path.join(self.instance_root,
                                 'var', 'xml_report', self.computer_id)

    # The directory xml_report contain a number of files equal
    # to the number of software instance running inside the same partition
    if os.path.isdir(computer_report_dir):
      filename_list = os.listdir(computer_report_dir)
    else:
      filename_list = []

    for filename in filename_list:

      file_path = os.path.join(computer_report_dir, filename)
      if os.path.exists(file_path):
        usage = open(file_path, 'r').read()

      if self.validateXML(usage, computer_consumption_model):
        self.logger.info('XML file generated by asXML is valid')
        slap_computer_usage.reportUsage(usage)
        filename_delete_list.append(filename)
      else:
        self.logger.info('XML file is invalid %s' % filename)

    # After sending the aggregated file we remove all the valid xml reports
    for filename in filename_delete_list:
      os.remove(os.path.join(computer_report_dir, filename))

    # If there is, at least, one report
    if computer_partition_usage_list != []:
      try:
        # We generate the final XML report with asXML method
        computer_consumption = self.asXML(computer_partition_usage_list)

        self.logger.info('Final xml report: %s' % computer_consumption)

        # We test the XML report before sending it
        if self.validateXML(computer_consumption, computer_consumption_model):
          self.logger.info('XML file generated by asXML is valid')
          slap_computer_usage.reportUsage(computer_consumption)
        else:
          self.logger.info('XML file generated by asXML is not valid !')
          raise ValueError('XML file generated by asXML is not valid !')
      except Exception:
        issue = "Cannot report usage for %r: %s" % (
            computer_partition.getId(),
            traceback.format_exc())
        self.logger.info(issue)
        computer_partition.error(issue, logger=self.logger)
        report_usage_issue_cp_list.append(computer_partition_id)

    for computer_partition in computer_partition_list:
      if computer_partition.getState() == COMPUTER_PARTITION_DESTROYED_STATE:
        destroyed = False
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
              _getSupervisordConfigurationDirectory(self.instance_root), '%s.conf' %
              computer_partition_id),
            supervisord_socket=self.supervisord_socket,
            computer_partition=computer_partition,
            computer_id=self.computer_id,
            partition_id=computer_partition_id,
            server_url=self.master_url,
            software_release_url=software_url,
            certificate_repository_path=self.certificate_repository_path,
            buildout=self.buildout,
            logger=self.logger,
            instance_storage_home=self.instance_storage_home,
            ipv4_global_network=self.ipv4_global_network,
          )
          local_partition.stop()
          try:
            computer_partition.stopped()
          except (SystemExit, KeyboardInterrupt):
            computer_partition.error(traceback.format_exc(), logger=self.logger)
            raise
          except Exception:
            pass
          # let managers update current partition
          for manager in self._manager_list:
            manager.report(local_partition)

          if computer_partition.getId() in report_usage_issue_cp_list:
            self.logger.info('Ignoring destruction of %r, as no report usage was sent' %
                                computer_partition.getId())
            continue
          if self._checkWaitProcessList(local_partition,
              state_list=['RUNNING', 'STARTING']):
            self.logger.info('There are running processes into the partition,' \
              ' wait until they finish...')
            continue
          destroyed = local_partition.destroy()
        except (SystemExit, KeyboardInterrupt):
          computer_partition.error(traceback.format_exc(), logger=self.logger)
          raise
        except Exception:
          clean_run = False
          self.logger.exception('')
          exc = traceback.format_exc()
          computer_partition.error(exc, logger=self.logger)
        try:
          if destroyed:
            computer_partition.destroyed()
        except NotFoundError:
          self.logger.debug('Ignored slap error while trying to inform about '
                            'destroying not fully configured Computer Partition %r' %
                                computer_partition.getId())
        except ServerError as server_error:
          self.logger.debug('Ignored server error while trying to inform about '
                            'destroying Computer Partition %r. Error is:\n%r' %
                                (computer_partition.getId(), server_error.args[0]))

    self.logger.info('Finished usage reports.')

    # Return success value
    if not clean_run:
      return SLAPGRID_FAIL
    return SLAPGRID_SUCCESS
