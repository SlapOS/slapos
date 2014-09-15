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
import textwrap
import xmlrpclib

from supervisor import xmlrpc

from slapos.grid.utils import (md5digest, getCleanEnvironment,
                               SlapPopen, dropPrivileges, updateFile)
from slapos.grid import utils  # for methods that could be mocked, access them through the module
from slapos.slap.slap import NotFoundError
from slapos.grid.svcbackend import getSupervisorRPC
from slapos.grid.exception import (BuildoutFailedError, WrongPermissionError,
                                   PathDoesNotExistError)
from slapos.grid.networkcache import download_network_cached, upload_network_cached


WATCHDOG_MARK = '-on-watch'

REQUIRED_COMPUTER_PARTITION_PERMISSION = 0o750

# XXX not very clean. this is changed when testing
PROGRAM_PARTITION_TEMPLATE = pkg_resources.resource_stream(__name__,
            'templates/program_partition_supervisord.conf.in').read()


class Software(object):
  """This class is responsible for installing a software release"""

  # XXX: "url" parameter should be named "key", "target" or alike to be more generic.
  #      The key is an url in the case of Buildout.
  def __init__(self, url, software_root, buildout, logger,
               signature_private_key_file=None, signature_certificate_list=None,
               upload_cache_url=None, upload_dir_url=None, shacache_cert_file=None,
               shacache_key_file=None, shadir_cert_file=None, shadir_key_file=None,
               download_binary_cache_url=None, upload_binary_cache_url=None,
               download_binary_dir_url=None, upload_binary_dir_url=None,
               download_from_binary_cache_url_blacklist=None,
               upload_to_binary_cache_url_blacklist=None):
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
    self.shacache_cert_file = shacache_cert_file
    self.shacache_key_file = shacache_key_file
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

  def install(self):
    """ Fetches binary cache if possible.
    Installs from buildout otherwise.
    """
    self.logger.info("Installing software release %s..." % self.url)
    cache_dir = tempfile.mkdtemp()
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
        ('shacache-cert-file', self.shacache_cert_file),
        ('shacache-key-file', self.shacache_key_file),
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
      fout.write(textwrap.dedent("""\
          # Created by slapgrid. extends {url}
          # but you can change it for development purposes.

          [buildout]
          extends =
            {url}
          """.format(url=url)))
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
        self.shacache_cert_file,
        self.shacache_key_file,
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
               ):
    """Initialisation of class parameters"""
    self.buildout = buildout
    self.logger = logger
    self.software_path = software_path
    self.instance_path = instance_path
    self.run_path = os.path.join(self.instance_path, 'etc', 'run')
    self.service_path = os.path.join(self.instance_path, 'etc', 'service')
    self.supervisord_partition_configuration_path = \
        supervisord_partition_configuration_path
    self.supervisord_socket = supervisord_socket
    self.computer_partition = computer_partition
    self.computer_id = computer_id
    self.partition_id = partition_id
    self.server_url = server_url
    self.software_release_url = software_release_url

    self.key_file = ''
    self.cert_file = ''
    if certificate_repository_path is not None:
      self.key_file = os.path.join(certificate_repository_path,
          self.partition_id + '.key')
      self.cert_file = os.path.join(certificate_repository_path,
          self.partition_id + '.crt')
      self._updateCertificate()

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

  def addServiceToGroup(self, partition_id, runner_list, path, extension=''):
    uid, gid = self.getUserGroupId()
    for runner in runner_list:
      self.partition_supervisor_configuration += '\n' + \
          PROGRAM_PARTITION_TEMPLATE % {
              'program_id': '_'.join([partition_id, runner]),
              'program_directory': self.instance_path,
              'program_command': os.path.join(path, runner),
              'program_name': runner + extension,
              'instance_path': self.instance_path,
              'user_id': uid,
              'group_id': gid,
              # As supervisord has no environment to inherit, setup a minimalistic one
              'HOME': pwd.getpwuid(uid).pw_dir,
              'USER': pwd.getpwuid(uid).pw_name,
          }

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
      self.logger.warning("Falling back to default buildout %r" %
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

  def generateSupervisorConfigurationFile(self):
    """
    Generates supervisord configuration file from template.

    check if CP/etc/run exists and it is a directory
    iterate over each file in CP/etc/run
    iterate over each file in CP/etc/service adding WatchdogID to their name
    if at least one is not 0o750 raise -- partition has something funny
    """
    runner_list = []
    service_list = []
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
      self.partition_supervisor_configuration = group_partition_template % {
          'instance_id': partition_id,
          'program_list': ','.join(['_'.join([partition_id, runner])
                                    for runner in runner_list + service_list])
      }
      # Same method to add to service and run
      self.addServiceToGroup(partition_id, runner_list, self.run_path)
      self.addServiceToGroup(partition_id, service_list, self.service_path,
                             extension=WATCHDOG_MARK)
      updateFile(self.supervisord_partition_configuration_path,
                 self.partition_supervisor_configuration)
    self.updateSupervisor()

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

      for root, dirs, file_list in os.walk(self.instance_path):
        for directory in dirs:
          shutil.rmtree(os.path.join(self.instance_path, directory))
        for file in file_list:
          os.remove(os.path.join(self.instance_path, file))

      if os.path.exists(self.supervisord_partition_configuration_path):
        os.remove(self.supervisord_partition_configuration_path)
      self.updateSupervisor()
    except IOError as exc:
      raise IOError("I/O error while freeing partition (%s): %s" % (self.instance_path, exc))

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
      supervisor.removeProcessGroup(gname)
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
