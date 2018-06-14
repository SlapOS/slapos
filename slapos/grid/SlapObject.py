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
import pwd
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import xmlrpclib

from supervisor import xmlrpc

from slapos.grid.utils import (md5digest, getCleanEnvironment,
                               SlapPopen, dropPrivileges, updateFile)
from slapos.grid import utils  # for methods that could be mocked, access them through the module
from slapos.slap.slap import NotFoundError
from slapos.grid.svcbackend import getSupervisorRPC
from slapos.grid.exception import (BuildoutFailedError, WrongPermissionError,
                                   PathDoesNotExistError, DiskSpaceError)
from slapos.grid.networkcache import download_network_cached, upload_network_cached
from slapos.human import bytes2human


WATCHDOG_MARK = '-on-watch'

REQUIRED_COMPUTER_PARTITION_PERMISSION = 0o750

CP_STORAGE_FOLDER_NAME = 'DATA'

# XXX not very clean. this is changed when testing
PROGRAM_PARTITION_TEMPLATE = pkg_resources.resource_stream(__name__,
            'templates/program_partition_supervisord.conf.in').read()


def free_space(path, fn):
  while True:
    try:
      disk = os.statvfs(path)
      return fn(disk)
    except OSError:
      pass
    if os.sep not in path:
      break
    path = os.path.split(path)[0]


def free_space_root(path):
  """
  Returns free space available to the root user, in bytes.

  A non-existent path can be provided, and the ancestors
  will be queried instead.
  """
  return free_space(path, lambda d: d.bsize * d.f_bfree)


def free_space_nonroot(path):
  """
  Returns free space available to non-root users, in bytes.

  A non-existent path can be provided, and the ancestors
  will be queried instead.
  """
  return free_space(path, lambda d: d.f_bsize * d.f_bavail)


class Software(object):
  """This class is responsible for installing a software release"""

  # XXX: "url" parameter should be named "key", "target" or alike to be more generic.
  #      The key is an url in the case of Buildout.
  def __init__(self, url, software_root, buildout, logger,
               signature_private_key_file=None, signature_certificate_list=None,
               upload_cache_url=None, upload_dir_url=None,
               shacache_ca_file=None, shacache_cert_file=None, shacache_key_file=None,
               shadir_ca_file=None, shadir_cert_file=None, shadir_key_file=None,
               download_binary_cache_url=None, upload_binary_cache_url=None,
               download_binary_dir_url=None, upload_binary_dir_url=None,
               download_from_binary_cache_url_blacklist=None,
               upload_to_binary_cache_url_blacklist=None,
               software_min_free_space=None):
    """Initialisation of class parameters
    """

    if download_from_binary_cache_url_blacklist is None:
      download_from_binary_cache_url_blacklist = []

    if upload_to_binary_cache_url_blacklist is None:
      upload_to_binary_cache_url_blacklist = []

    self.url = url
    self.software_root = software_root
    self.software_url_hash = md5digest(self.url)
    self.software_path = os.path.join(self.software_root,
                                      self.software_url_hash)
    self.buildout = buildout
    self.logger = logger
    self.signature_private_key_file = signature_private_key_file
    self.signature_certificate_list = signature_certificate_list
    self.upload_cache_url = upload_cache_url
    self.upload_dir_url = upload_dir_url
    self.shacache_ca_file = shacache_ca_file
    self.shacache_cert_file = shacache_cert_file
    self.shacache_key_file = shacache_key_file
    self.shadir_ca_file = shadir_ca_file
    self.shadir_cert_file = shadir_cert_file
    self.shadir_key_file = shadir_key_file
    self.download_binary_cache_url = download_binary_cache_url
    self.upload_binary_cache_url = upload_binary_cache_url
    self.download_binary_dir_url = download_binary_dir_url
    self.upload_binary_dir_url = upload_binary_dir_url
    self.download_from_binary_cache_url_blacklist = \
        download_from_binary_cache_url_blacklist
    self.upload_to_binary_cache_url_blacklist = \
        upload_to_binary_cache_url_blacklist
    self.software_min_free_space = software_min_free_space

  def check_free_space(self):
    required = self.software_min_free_space
    available = free_space_nonroot(self.software_path)

    if available < required:
      msg = "Not enough space for {path}: available {available}, required {required} (option 'software_min_free_space')"
      raise DiskSpaceError(msg.format(path=self.software_path,
                                      available=bytes2human(available),
                                      required=bytes2human(required)))

  def install(self):
    """ Fetches binary cache if possible.
    Installs from buildout otherwise.
    """
    self.logger.info("Installing software release %s..." % self.url)
    cache_dir = tempfile.mkdtemp()

    self.check_free_space()

    try:
      tarpath = os.path.join(cache_dir, self.software_url_hash)
      # Check if we can download from cache
      if (not os.path.exists(self.software_path)) \
          and download_network_cached(
              self.download_binary_cache_url,
              self.download_binary_dir_url,
              self.url, self.software_root,
              self.software_url_hash,
              tarpath, self.logger,
              self.signature_certificate_list,
              self.download_from_binary_cache_url_blacklist):
        tar = tarfile.open(tarpath)
        try:
          self.logger.info("Extracting archive of cached software release...")
          tar.extractall(path=self.software_root)
        finally:
          tar.close()
      else:
        self._install_from_buildout()
        # Upload to binary cache if possible and allowed
        if all([self.software_root, self.url, self.software_url_hash,
                self.upload_binary_cache_url, self.upload_binary_dir_url]):
          blacklisted = False
          for url in self.upload_to_binary_cache_url_blacklist:
            if self.url.startswith(url):
              blacklisted = True
              self.logger.info("Can't upload to binary cache: "
                               "Software Release URL is blacklisted.")
              break
          if not blacklisted:
            self.uploadSoftwareRelease(tarpath)
    finally:
      shutil.rmtree(cache_dir)

  def _set_ownership(self, path):
    """
    If running as root: copy ownership of software_root to path
    If not running as root: do nothing
    """
    if os.getuid():
      return
    root_stat = os.stat(self.software_root)
    path_stat = os.stat(path)
    if (root_stat.st_uid != path_stat.st_uid or
          root_stat.st_gid != path_stat.st_gid):
      os.chown(path, root_stat.st_uid, root_stat.st_gid)

  def _additional_buildout_parameters(self, extends_cache):
    yield 'buildout:extends-cache=%s' % extends_cache
    yield 'buildout:directory=%s' % self.software_path

    if (self.signature_private_key_file or
          self.upload_cache_url or
          self.upload_dir_url):
      yield 'buildout:networkcache-section=networkcache'

    for networkcache_option, value in [
        ('signature-private-key-file', self.signature_private_key_file),
        ('upload-cache-url', self.upload_cache_url),
        ('upload-dir-url', self.upload_dir_url),
        ('shacache-ca-file', self.shacache_ca_file),
        ('shacache-cert-file', self.shacache_cert_file),
        ('shacache-key-file', self.shacache_key_file),
        ('shadir-ca-file', self.shadir_ca_file),
        ('shadir-cert-file', self.shadir_cert_file),
        ('shadir-key-file', self.shadir_key_file)
    ]:
      if value:
        yield 'networkcache:%s=%s' % (networkcache_option, value)

  def _install_from_buildout(self):
    """ Fetches buildout configuration from the server, run buildout with
    it. If it fails, we notify the server.
    """
    root_stat = os.stat(self.software_root)
    os.environ = getCleanEnvironment(logger=self.logger,
                                     home_path=pwd.getpwuid(root_stat.st_uid).pw_dir)
    if not os.path.isdir(self.software_path):
      os.mkdir(self.software_path)
      self._set_ownership(self.software_path)
      os.chmod(self.software_path, 0o755)

    extends_cache = tempfile.mkdtemp()
    self._set_ownership(extends_cache)

    try:
      buildout_cfg = os.path.join(self.software_path, 'buildout.cfg')
      if not os.path.exists(buildout_cfg):
        self._create_buildout_profile(buildout_cfg, self.url)

      additional_parameters = list(self._additional_buildout_parameters(extends_cache))
      additional_parameters.extend(['-c', buildout_cfg])

      utils.bootstrapBuildout(path=self.software_path,
                              buildout=self.buildout,
                              logger=self.logger,
                              additional_buildout_parameter_list=additional_parameters)

      utils.launchBuildout(path=self.software_path,
                           buildout_binary=os.path.join(self.software_path, 'bin', 'buildout'),
                           logger=self.logger,
                           additional_buildout_parameter_list=additional_parameters)
    finally:
      shutil.rmtree(extends_cache)

  def _create_buildout_profile(self, buildout_cfg, url):
    with open(buildout_cfg, 'wb') as fout:
      fout.write('[buildout]\nextends = ' + url + '\n')
    self._set_ownership(buildout_cfg)

  def uploadSoftwareRelease(self, tarpath):
    """
    Try to tar and upload an installed Software Release.
    """
    self.logger.info("Creating archive of software release...")
    tar = tarfile.open(tarpath, "w:gz")
    try:
      tar.add(self.software_path, arcname=self.software_url_hash)
    finally:
      tar.close()
    self.logger.info("Trying to upload archive of software release...")
    upload_network_cached(
        self.software_root,
        self.url, self.software_url_hash,
        self.upload_binary_cache_url,
        self.upload_binary_dir_url,
        tarpath, self.logger,
        self.signature_private_key_file,
        self.shacache_ca_file,
        self.shacache_cert_file,
        self.shacache_key_file,
        self.shadir_ca_file,
        self.shadir_cert_file,
        self.shadir_key_file)

  def destroy(self):
    """Removes software release."""
    def retry(func, path, exc):
      # inspired by slapos.buildout hard remover
      if func == os.path.islink:
        os.unlink(path)
      else:
        os.chmod(path, 0o600)
        func(path)
    try:
      if os.path.exists(self.software_path):
        self.logger.info('Removing path %r' % self.software_path)
        shutil.rmtree(self.software_path, onerror=retry)
      else:
        self.logger.info('Path %r does not exists, no need to remove.' %
            self.software_path)
    except IOError as exc:
      raise IOError("I/O error while removing software (%s): %s" % (self.url, exc))


class Partition(object):
  """This class is responsible of the installation of an instance
  """
  retention_lock_delay_filename = '.slapos-retention-lock-delay'
  retention_lock_date_filename = '.slapos-retention-lock-date'
  partition_firewall_rules_name = '.slapos-firewalld-rules'

  # XXX: we should give the url (or the "key") instead of the software_path
  #      then compute the path from it, like in Software.
  def __init__(self,
               software_path,
               instance_path,
               supervisord_partition_configuration_path,
               supervisord_socket,
               computer_partition,
               computer_id,
               partition_id,
               server_url,
               software_release_url,
               buildout,
               logger,
               certificate_repository_path=None,
               retention_delay='0',
               instance_min_free_space=None,
               instance_storage_home='',
               ipv4_global_network='',
               ):
    """Initialisation of class parameters"""
    self.buildout = buildout
    self.logger = logger
    self.software_path = software_path
    self.instance_path = instance_path
    self.run_path = os.path.join(self.instance_path, 'etc', 'run')
    self.service_path = os.path.join(self.instance_path, 'etc', 'service')
    self.prerm_path = os.path.join(self.instance_path, 'etc', 'prerm')
    self.supervisord_partition_configuration_path = \
        supervisord_partition_configuration_path
    self.supervisord_socket = supervisord_socket
    self.computer_partition = computer_partition
    self.computer_id = computer_id
    self.partition_id = partition_id
    self.server_url = server_url
    self.software_release_url = software_release_url
    self.instance_storage_home = instance_storage_home
    self.ipv4_global_network = ipv4_global_network

    self.key_file = ''
    self.cert_file = ''
    if certificate_repository_path is not None:
      self.key_file = os.path.join(certificate_repository_path,
          self.partition_id + '.key')
      self.cert_file = os.path.join(certificate_repository_path,
          self.partition_id + '.crt')
      self._updateCertificate()

    try:
      self.retention_delay = float(retention_delay)
    except ValueError:
      self.logger.warn('Retention delay value (%s) is not valid, ignoring.' \
                       % self.retention_delay)
      self.retention_delay = 0

    self.retention_lock_delay_file_path = os.path.join(
        self.instance_path, self.retention_lock_delay_filename
    )
    self.retention_lock_date_file_path = os.path.join(
        self.instance_path, self.retention_lock_date_filename
    )
    self.firewall_rules_path = os.path.join(
        self.instance_path, self.partition_firewall_rules_name
    )

    self.instance_min_free_space = instance_min_free_space


  def check_free_space(self):
    required = self.instance_min_free_space
    available = free_space_nonroot(self.instance_path)

    if available < required:
      msg = "Not enough space for {path}: available {available}, required {required} (option 'instance_min_free_space')"
      raise DiskSpaceError(msg.format(path=self.instance_path,
                                      available=bytes2human(available),
                                      required=bytes2human(required)))

  def _updateCertificate(self):
    try:
      partition_certificate = self.computer_partition.getCertificate()
    except NotFoundError:
      raise NotFoundError('Partition %s is not known by SlapOS Master.' %
          self.partition_id)

    uid, gid = self.getUserGroupId()

    for name, path in [('certificate', self.cert_file), ('key', self.key_file)]:
      new_content = partition_certificate[name]
      old_content = None
      if os.path.exists(path):
        old_content = open(path).read()

      if old_content != new_content:
        if old_content is None:
          self.logger.info('Missing %s file. Creating %r' % (name, path))
        else:
          self.logger.info('Changed %s content. Updating %r' % (name, path))

        with os.fdopen(os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o400), 'wb') as fout:
          fout.write(new_content)
        os.chown(path, uid, gid)

  def getUserGroupId(self):
    """Returns tuple of (uid, gid) of partition"""
    stat_info = os.stat(self.instance_path)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    return (uid, gid)

  def addProgramToGroup(self, partition_id, program_id, name, command,
                        as_user=True):
    if as_user:
      uid, gid = self.getUserGroupId()
    else:
      uid, gid = 0, 0
    self.partition_supervisor_configuration += '\n' + \
      PROGRAM_PARTITION_TEMPLATE % {
        'program_id': '{}_{}'.format(partition_id, program_id),
        'program_directory': self.instance_path,
        'program_command': command,
        'program_name': name,
        'instance_path': self.instance_path,
        'user_id': uid,
        'group_id': gid,
        # As supervisord has no environment to inherit, setup a minimalistic one
        'HOME': pwd.getpwuid(uid).pw_dir,
        'USER': pwd.getpwuid(uid).pw_name,
      }

  def addCustomGroup(self, group_suffix, partition_id, program_list):
    group_partition_template = pkg_resources.resource_stream(__name__,
      'templates/group_partition_supervisord.conf.in').read()
    group_id = '{}-{}'.format(partition_id, group_suffix)

    self.supervisor_configuration_group += group_partition_template % {
      'instance_id': group_id,
      'program_list': ','.join(['{}_{}'.format(group_id, program_id)
                                for program_id in program_list]),
    }

    return group_id

  def addServiceToGroup(self, partition_id, runner_list, path, extension=''):
    for runner in runner_list:
      program_id = runner
      program_name = runner + extension
      program_command = os.path.join(path, runner)
      self.addProgramToGroup(partition_id, program_id, program_name,
                             program_command)

  def addServiceToCustomGroup(self, group_suffix, partition_id, runner_list,
      path, extension=''):
    """Add new services to supervisord that belong to specific group"""
    group_id = self.addCustomGroup(group_suffix, partition_id,
                                   runner_list)
    return self.addServiceToGroup(group_id, runner_list, path, extension)

  def updateSymlink(self, sr_symlink, software_path):
    if os.path.lexists(sr_symlink):
      if not os.path.islink(sr_symlink):
        self.logger.debug('Not a symlink: %s, has been ignored' % sr_symlink)
        return
      os.unlink(sr_symlink)
    os.symlink(software_path, sr_symlink)
    os.lchown(sr_symlink, *self.getUserGroupId())

  def install(self):
    """ Creates configuration file from template in software_path, then
    installs the software partition with the help of buildout
    """
    self.logger.info("Installing Computer Partition %s..."
        % self.computer_partition.getId())

    self.check_free_space()

    # Checks existence and permissions of Partition directory
    # Note : Partitions have to be created and configured before running slapgrid
    if not os.path.isdir(self.instance_path):
      raise PathDoesNotExistError('Please create partition directory %s'
                                           % self.instance_path)

    sr_symlink = os.path.join(self.instance_path, 'software_release')
    self.updateSymlink(sr_symlink, self.software_path)

    instance_stat_info = os.stat(self.instance_path)
    permission = stat.S_IMODE(instance_stat_info.st_mode)
    if permission != REQUIRED_COMPUTER_PARTITION_PERMISSION:
      raise WrongPermissionError('Wrong permissions in %s: actual '
                                 'permissions are: 0%o, wanted are 0%o' %
                                 (self.instance_path, permission,
                                  REQUIRED_COMPUTER_PARTITION_PERMISSION))
    os.environ = getCleanEnvironment(logger=self.logger,
                                     home_path=pwd.getpwuid(instance_stat_info.st_uid).pw_dir)

    # Check that Software Release directory is present
    if not os.path.exists(self.software_path):
      # XXX What should it raise?
      raise IOError('Software Release %s is not present on system.\n'
                    'Cannot deploy instance.' % self.software_release_url)

    # Generate buildout instance profile from template in Software Release
    template_location = os.path.join(self.software_path, 'instance.cfg')
    if not os.path.exists(template_location):
      # Backward compatibility: "instance.cfg" file was named "template.cfg".
      if os.path.exists(os.path.join(self.software_path, 'template.cfg')):
        template_location = os.path.join(self.software_path, 'template.cfg')
      else:
        # No template: Software Release is either inconsistent or not correctly installed.
        # XXX What should it raise?
        raise IOError('Software Release %s is not correctly installed.\nMissing file: %s' % (
            self.software_release_url, template_location))
    config_location = os.path.join(self.instance_path, 'buildout.cfg')
    self.logger.debug("Copying %r to %r" % (template_location, config_location))
    shutil.copy(template_location, config_location)

    # fill generated buildout with additional information
    buildout_text = open(config_location).read()
    buildout_text += '\n\n' + pkg_resources.resource_string(__name__,
        'templates/buildout-tail.cfg.in') % {
            'computer_id': self.computer_id,
            'partition_id': self.partition_id,
            'server_url': self.server_url,
            'software_release_url': self.software_release_url,
            'key_file': self.key_file,
            'cert_file': self.cert_file,
            'storage_home': self.instance_storage_home,
            'global_ipv4_network_prefix': self.ipv4_global_network,
        }
    open(config_location, 'w').write(buildout_text)
    os.chmod(config_location, 0o640)
    # Try to find the best possible buildout:
    #  *) if software_root/bin/bootstrap exists use this one to bootstrap
    #     locally
    #  *) as last resort fallback to buildout binary from software_path
    bootstrap_candidate_dir = os.path.abspath(os.path.join(self.software_path,
      'bin'))
    if os.path.isdir(bootstrap_candidate_dir):
      bootstrap_candidate_list = [q for q in os.listdir(bootstrap_candidate_dir)
        if q.startswith('bootstrap')]
    else:
      bootstrap_candidate_list = []
    uid, gid = self.getUserGroupId()
    os.chown(config_location, -1, int(gid))
    if len(bootstrap_candidate_list) == 0:
      buildout_binary = os.path.join(self.software_path, 'bin', 'buildout')
      self.logger.info("Falling back to default buildout %r" %
        buildout_binary)
    else:
      if len(bootstrap_candidate_list) != 1:
        raise ValueError('More than one bootstrap candidate found.')
      # Reads uid/gid of path, launches buildout with thoses privileges
      bootstrap_file = os.path.abspath(os.path.join(bootstrap_candidate_dir,
        bootstrap_candidate_list[0]))

      first_line = open(bootstrap_file, 'r').readline()
      invocation_list = []
      if first_line.startswith('#!'):
        invocation_list = first_line[2:].split()
      invocation_list.append(bootstrap_file)

      self.logger.debug('Invoking %r in %r' % (' '.join(invocation_list),
        self.instance_path))
      process_handler = SlapPopen(invocation_list,
                                  preexec_fn=lambda: dropPrivileges(uid, gid, logger=self.logger),
                                  cwd=self.instance_path,
                                  env=getCleanEnvironment(logger=self.logger,
                                                          home_path=pwd.getpwuid(uid).pw_dir),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  logger=self.logger)
      if process_handler.returncode is None or process_handler.returncode != 0:
        message = 'Failed to bootstrap buildout in %r.' % (self.instance_path)
        self.logger.error(message)
        raise BuildoutFailedError('%s:\n%s\n' % (message, process_handler.output))
      buildout_binary = os.path.join(self.instance_path, 'sbin', 'buildout')

    if not os.path.exists(buildout_binary):
      # use own buildout generation
      utils.bootstrapBuildout(path=self.instance_path,
                              buildout=self.buildout,
                              logger=self.logger,
                              additional_buildout_parameter_list=
                                ['buildout:bin-directory=%s' %
                                    os.path.join(self.instance_path, 'sbin')])
      buildout_binary = os.path.join(self.instance_path, 'sbin', 'buildout')

    # Launches buildout
    utils.launchBuildout(path=self.instance_path,
                         buildout_binary=buildout_binary,
                         logger=self.logger)
    self.generateSupervisorConfigurationFile()
    self.createRetentionLockDelay()

  def generateSupervisorConfiguration(self):
    """
    Generates supervisord configuration file from template.

    check if CP/etc/run exists and it is a directory
    iterate over each file in CP/etc/run
    iterate over each file in CP/etc/service adding WatchdogID to their name
    if at least one is not 0o750 raise -- partition has something funny
    """
    runner_list = []
    service_list = []
    self.partition_supervisor_configuration = ""
    self.supervisor_configuration_group = ""
    if os.path.exists(self.run_path):
      if os.path.isdir(self.run_path):
        runner_list = os.listdir(self.run_path)
    if os.path.exists(self.service_path):
      if os.path.isdir(self.service_path):
        service_list = os.listdir(self.service_path)
    if len(runner_list) == 0 and len(service_list) == 0:
      self.logger.warning('No runners nor services found for partition %r' %
          self.partition_id)
      if os.path.exists(self.supervisord_partition_configuration_path):
        os.unlink(self.supervisord_partition_configuration_path)
    else:
      partition_id = self.computer_partition.getId()
      group_partition_template = pkg_resources.resource_stream(__name__,
          'templates/group_partition_supervisord.conf.in').read()
      self.supervisor_configuration_group = group_partition_template % {
          'instance_id': partition_id,
          'program_list': ','.join(['_'.join([partition_id, runner])
                                    for runner in runner_list + service_list])
      }
      # Same method to add to service and run
      self.addServiceToGroup(partition_id, runner_list, self.run_path)
      self.addServiceToGroup(partition_id, service_list, self.service_path,
                             extension=WATCHDOG_MARK)

  def writeSupervisorConfigurationFile(self):
    """
      Write supervisord configuration file and update supervisord
    """
    if self.supervisor_configuration_group and \
        self.partition_supervisor_configuration:
      updateFile(self.supervisord_partition_configuration_path,
                 self.supervisor_configuration_group +
                 self.partition_supervisor_configuration)
    self.updateSupervisor()

  def generateSupervisorConfigurationFile(self):
    """
      update supervisord with new processes
    """
    self.generateSupervisorConfiguration()
    self.writeSupervisorConfigurationFile()

  def start(self):
    """Asks supervisord to start the instance. If this instance is not
    installed, we install it.
    """
    supervisor = self.getSupervisorRPC()
    partition_id = self.computer_partition.getId()
    try:
      supervisor.startProcessGroup(partition_id, False)
    except xmlrpclib.Fault as exc:
      if exc.faultString.startswith('BAD_NAME:'):
        self.logger.info("Nothing to start on %s..." %
                         self.computer_partition.getId())
    else:
      self.logger.info("Requested start of %s..." % self.computer_partition.getId())

  def stop(self):
    """Asks supervisord to stop the instance."""
    partition_id = self.computer_partition.getId()
    try:
      supervisor = self.getSupervisorRPC()
      supervisor.stopProcessGroup(partition_id, False)
    except xmlrpclib.Fault as exc:
      if exc.faultString.startswith('BAD_NAME:'):
        self.logger.info('Partition %s not known in supervisord, ignoring' % partition_id)
    else:
      self.logger.info("Requested stop of %s..." % self.computer_partition.getId())

  def destroy(self):
    """Destroys the partition and makes it available for subsequent use."
    """
    self.logger.info("Destroying Computer Partition %s..."
        % self.computer_partition.getId())

    self.createRetentionLockDate()
    if not self.checkRetentionIsAuthorized():
      return False

    # Launches "destroy" binary if exists
    destroy_executable_location = os.path.join(self.instance_path, 'sbin',
        'destroy')
    if os.path.exists(destroy_executable_location):
      uid, gid = self.getUserGroupId()
      self.logger.debug('Invoking %r' % destroy_executable_location)
      process_handler = SlapPopen([destroy_executable_location],
                                  preexec_fn=lambda: dropPrivileges(uid, gid, logger=self.logger),
                                  cwd=self.instance_path,
                                  env=getCleanEnvironment(logger=self.logger,
                                                          home_path=pwd.getpwuid(uid).pw_dir),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  logger=self.logger)
      if process_handler.returncode is None or process_handler.returncode != 0:
        message = 'Failed to destroy Computer Partition in %r.' % \
            self.instance_path
        self.logger.error(message)
        raise subprocess.CalledProcessError(message, process_handler.output)
    # Manually cleans what remains
    try:
      for f in [self.key_file, self.cert_file]:
        if f:
          if os.path.exists(f):
            os.unlink(f)

      # better to manually remove symlinks because rmtree might choke on them
      sr_symlink = os.path.join(self.instance_path, 'software_release')
      if os.path.islink(sr_symlink):
        os.unlink(sr_symlink)
      data_base_link = os.path.join(self.instance_path, CP_STORAGE_FOLDER_NAME)
      if self.instance_storage_home and os.path.exists(data_base_link) and \
                                os.path.isdir(data_base_link):
        for filename in os.listdir(data_base_link):
          data_symlink = os.path.join(data_base_link, filename)
          partition_data_path = os.path.join(self.instance_storage_home,
                                                    filename, self.partition_id)
          if os.path.lexists(data_symlink):
            os.unlink(data_symlink)
          if os.path.exists(partition_data_path):
            self.cleanupFolder(partition_data_path)

      self.cleanupFolder(self.instance_path)
      
      # Cleanup all Data storage location of this partition
      

      if os.path.exists(self.supervisord_partition_configuration_path):
        os.remove(self.supervisord_partition_configuration_path)
      self.updateSupervisor()
    except IOError as exc:
      raise IOError("I/O error while freeing partition (%s): %s" % (self.instance_path, exc))

    return True

  def checkProcessesFromStateList(self, process_list, state_list):
    """Asks supervisord to check if one of the processes are in the state_list."""
    supervisor = self.getSupervisorRPC()
    for process in process_list:
      try:
        info = supervisor.getProcessInfo(process)
        if info['statename'] in state_list:
          return True
      except xmlrpclib.Fault as exc:
        self.logger.debug("BAD process name: %r" % process)
        continue
    return False

  def cleanupFolder(self, folder_path):
    """Delete all files and folders in a specified directory
    """
    for root, dirs, file_list in os.walk(folder_path):
      for directory in dirs:
        shutil.rmtree(os.path.join(folder_path, directory))
      for file in file_list:
        os.remove(os.path.join(folder_path, file))

  def fetchInformations(self):
    """Fetch usage informations with buildout, returns it.
    """
    raise NotImplementedError

  def getSupervisorRPC(self):
    return getSupervisorRPC(self.supervisord_socket)

  def updateSupervisor(self):
    """Forces supervisord to reload its configuration"""
    # Note: This method shall wait for results from supervisord
    #       In future it will not be needed, as update command
    #       is going to be implemented on server side.
    self.logger.debug('Updating supervisord')
    supervisor = self.getSupervisorRPC()
    # took from supervisord.supervisorctl.do_update
    result = supervisor.reloadConfig()
    added, changed, removed = result[0]

    for gname in removed:
      results = supervisor.stopProcessGroup(gname)
      fails = [res for res in results
               if res['status'] == xmlrpc.Faults.FAILED]
      if fails:
        self.logger.warning('Problem while stopping process %r, will try later' % gname)
      else:
        self.logger.info('Stopped %r' % gname)
      for i in xrange(0, 10):
        # Some process may be still running, be nice and wait for them to be stopped.
        try:
          supervisor.removeProcessGroup(gname)
          break
        except:
          if i == 9:
            raise
          time.sleep(1)

      self.logger.info('Removed %r' % gname)

    for gname in changed:
      results = supervisor.stopProcessGroup(gname)
      self.logger.info('Stopped %r' % gname)

      supervisor.removeProcessGroup(gname)
      supervisor.addProcessGroup(gname)
      self.logger.info('Updated %r' % gname)

    for gname in added:
      supervisor.addProcessGroup(gname)
      self.logger.info('Updated %r' % gname)
    self.logger.debug('Supervisord updated')

  def _set_ownership(self, path):
    """
    If running as root: copy ownership of software_path to path
    If not running as root: do nothing
    """
    if os.getuid():
      return
    root_stat = os.stat(self.software_path)
    path_stat = os.stat(path)
    if (root_stat.st_uid != path_stat.st_uid or
          root_stat.st_gid != path_stat.st_gid):
      os.chown(path, root_stat.st_uid, root_stat.st_gid)

  def checkRetentionIsAuthorized(self):
    """
    Check if retention is authorized by checking retention lock delay or
    retention lock date.

    A retention lock delay is a delay which is:
     * Defined by the user/machine who requested the instance
     * Hardcoded the first time the instance is deployed, then is read-only
       during the whole lifetime of the instance
     * Triggered the first time the instance is requested to be destroyed
       (retention will be ignored).
       From this point, it is not possible to destroy the instance until the
       delay is over.
     * Accessible in read-only mode from the partition

    A retention lock date is the date computed from (date of first
    retention request + retention lock delay in days).

    Example:
     * User requests an instance with delay as 10 (days) to a SlapOS Master
     * SlapOS Master transmits this information to the SlapOS Node (current code)
     * SlapOS Node hardcodes this delay at first deployment
     * User requests retention of instance
     * SlapOS Node tries to destroy for the first time: it doesn't actually
       destroy, but it triggers the creation of a retention lock date from
       from the hardcoded delay. At this point it is not possible to
       destroy instance until current date + 10 days.
     * SlapOS Node continues to try to destroy: it doesn't do anything until
       retention lock date is reached.
    """
    retention_lock_date = self.getExistingRetentionLockDate()
    now = time.time()
    if not retention_lock_date:
      if self.getExistingRetentionLockDelay() > 0:
        self.logger.info('Impossible to destroy partition yet because of retention lock.')
        return False
      # Else: OK to destroy
    else:
      if now < retention_lock_date:
        self.logger.info('Impossible to destroy partition yet because of retention lock.')
        return False
      # Else: OK to destroy
    return True

  def createRetentionLockDelay(self):
    """
    Create a retention lock delay for the current partition.
    If retention delay is not specified, create it wth "0" as value
    """
    if os.path.exists(self.retention_lock_delay_file_path):
      return
    with open(self.retention_lock_delay_file_path, 'w') as delay_file_path:
      delay_file_path.write(str(self.retention_delay))
    self._set_ownership(self.retention_lock_delay_file_path)

  def getExistingRetentionLockDelay(self):
    """
    Return the retention lock delay of current partition (created at first
    deployment) if exist.
    Return -1 otherwise.
    """
    retention_delay = -1
    if os.path.exists(self.retention_lock_delay_file_path):
      with open(self.retention_lock_delay_file_path) as delay_file_path:
        retention_delay = float(delay_file_path.read())
    return retention_delay

  def createRetentionLockDate(self):
    """
    If retention lock delay > 0:
    Create a retention lock date for the current partition from the
    retention lock delay.
    Do nothing otherwise.
    """
    if os.path.exists(self.retention_lock_date_file_path):
      return
    retention_delay = self.getExistingRetentionLockDelay()
    if retention_delay <= 0:
      return
    now = int(time.time())
    retention_date = now + retention_delay * 24 * 3600
    with open(self.retention_lock_date_file_path, 'w') as date_file_path:
      date_file_path.write(str(retention_date))
    self._set_ownership(self.retention_lock_date_file_path)

  def getExistingRetentionLockDate(self):
    """
    Return the retention lock delay of current partition if exist.
    Return None otherwise.
    """
    if os.path.exists(self.retention_lock_date_file_path):
      with open(self.retention_lock_date_file_path) as date_file_path:
        return float(date_file_path.read())
    else:
      return None
