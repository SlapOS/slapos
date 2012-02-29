##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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
import logging
import os
import shutil
import subprocess
import pkg_resources
import stat
import tempfile
from supervisor import xmlrpc
import xmlrpclib
import pwd
import utils
from svcbackend import getSupervisorRPC
from exception import BuildoutFailedError, WrongPermissionError, \
    PathDoesNotExistError
from networkcache import download_network_cached, upload_network_cached
import tarfile

REQUIRED_COMPUTER_PARTITION_PERMISSION = '0750'


class Software(object):
  """This class is responsible of installing a software release"""
  def __init__(self, url, software_root, console, buildout,
      signature_private_key_file=None, signature_certificate_list=None,
      upload_cache_url=None, upload_dir_url=None, shacache_cert_file=None,
      shacache_key_file=None, shadir_cert_file=None, shadir_key_file=None,
      download_binary_cache_url=None, upload_binary_cache_url=None,
      download_binary_dir_url=None, upload_binary_dir_url=None):
    """Initialisation of class parameters
    """
    self.url = url
    self.software_root = software_root
    self.software_url_hash = utils.getSoftwareUrlHash(self.url)
    self.software_path = os.path.join(self.software_root,
                                      self.software_url_hash)
    self.buildout = buildout
    self.logger = logging.getLogger('BuildoutManager')
    self.console = console
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

  def install(self):
    """ Fetches binary cache if possible.
    Installs from buildout otherwise.
    """
    tarname = self.software_url_hash
    cache_dir = tempfile.mkdtemp()
    tarpath = os.path.join(cache_dir, tarname)
    if (not os.path.exists(self.software_path)) \
      and download_network_cached(
          self.download_binary_cache_url,
          self.download_binary_dir_url,
          self.url, self.software_root,
          self.software_url_hash,
          tarpath, self.logger,
          self.signature_certificate_list):
        tar = tarfile.open(tarpath)
        try:
          self.logger.info("Extracting archive of cached software release...")
          tar.extractall(path=self.software_root)
        finally:
          tar.close()
    else:
        self._install_from_buildout()
        if (self.software_root and self.url and self.software_url_hash \
                               and self.upload_binary_cache_url \
                               and self.upload_binary_dir_url):
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
    shutil.rmtree(cache_dir)
      
  def _install_from_buildout(self):
    """ Fetches buildout configuration from the server, run buildout with
    it. If it fails, we notify the server.
    """
    self.logger.info("Installing software release %s..." % self.url)
    root_stat_info = os.stat(self.software_root)
    os.environ = utils.getCleanEnvironment(pwd.getpwuid(root_stat_info.st_uid
      ).pw_dir)
    if not os.path.isdir(self.software_path):
      os.mkdir(self.software_path)
    extends_cache = tempfile.mkdtemp()
    if os.getuid() == 0:
      # In case when running as root copy ownership, to simplify logic
      for path in [self.software_path, extends_cache]:
        path_stat_info = os.stat(path)
        if root_stat_info.st_uid != path_stat_info.st_uid or\
             root_stat_info.st_gid != path_stat_info.st_gid:
            os.chown(path, root_stat_info.st_uid,
                root_stat_info.st_gid)
    try:
      buildout_parameter_list = [
        'buildout:extends-cache=%s' % extends_cache,
        'buildout:directory=%s' % self.software_path,]

      if self.signature_private_key_file or \
          self.upload_cache_url or \
            self.upload_dir_url is not None:
        buildout_parameter_list.append('buildout:networkcache-section=networkcache')
      for  buildout_option, value in (
         ('%ssignature-private-key-file=%s', self.signature_private_key_file),
         ('%supload-cache-url=%s', self.upload_cache_url),
         ('%supload-dir-url=%s', self.upload_dir_url),
         ('%sshacache-cert-file=%s', self.shacache_cert_file),
         ('%sshacache-key-file=%s', self.shacache_key_file),
         ('%sshadir-cert-file=%s', self.shadir_cert_file),
         ('%sshadir-key-file=%s', self.shadir_key_file),
         ):
        if value:
          buildout_parameter_list.append( \
              buildout_option % ('networkcache:', value))

      buildout_parameter_list.extend(['-c', self.url])
      utils.bootstrapBuildout(self.software_path, self.buildout,
          additional_buildout_parametr_list=buildout_parameter_list,
          console=self.console)
      utils.launchBuildout(self.software_path,
                     os.path.join(self.software_path, 'bin', 'buildout'),
                     additional_buildout_parametr_list=buildout_parameter_list,
                     console=self.console)
    finally:
      shutil.rmtree(extends_cache)

  def remove(self):
    """Removes the part that was installed.
    """
    try:
      shutil.rmtree(self.software_path)
    except IOError as error:
      error_string = "I/O error while removing software (%s): %s" % (self.url,
                                                                     error)
      raise IOError(error_string)


class Partition(object):
  """This class is responsible of the installation of a instance
  """
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
               certificate_repository_path=None,
               console=False
               ):
    """Initialisation of class parameters"""
    self.buildout = buildout
    self.software_path = software_path
    self.instance_path = instance_path
    self.run_path = os.path.join(self.instance_path, 'etc', 'run')
    self.supervisord_partition_configuration_path = \
        supervisord_partition_configuration_path
    self.supervisord_socket = supervisord_socket
    self.computer_partition = computer_partition
    self.logger = logging.getLogger('Partition')
    self.computer_id = computer_id
    self.partition_id = partition_id
    self.server_url = server_url
    self.software_release_url = software_release_url
    self.console = console

    self.key_file = ''
    self.cert_file = ''
    if certificate_repository_path is not None:
      self.key_file = os.path.join(certificate_repository_path,
          self.partition_id + '.key')
      self.cert_file = os.path.join(certificate_repository_path,
          self.partition_id + '.crt')
      self._updateCertificate()

  def _updateCertificate(self):
    if not os.path.exists(self.key_file) or \
        not os.path.exists(self.cert_file):
      self.logger.info('Certificate and key not found, downloading to %r and '
          '%r' % (self.cert_file, self.key_file))
      partition_certificate = self.computer_partition.getCertificate()
      open(self.key_file, 'w').write(partition_certificate['key'])
      open(self.cert_file, 'w').write(partition_certificate['certificate'])
    for f in [self.key_file, self.cert_file]:
      os.chmod(f, 0400)
      os.chown(f, *self.getUserGroupId())

  def getUserGroupId(self):
    """Returns tuple of (uid, gid) of partition"""
    stat_info = os.stat(self.instance_path)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    return (uid, gid)

  def install(self):
    """ Creates configuration file from template in software_path, then
    installs the software partition with the help of buildout
    """
    # XXX: Shall be no op in case if revision had not changed
    #      It requires implementation of revision on server
    self.logger.info("Installing Computer Partition %s..." \
        % self.computer_partition.getId())
    # Checks existence and permissions of Partition directory
    # Note : Partitions have to be created and configured before running slapgrid
    if not os.path.isdir(self.instance_path):
      raise PathDoesNotExistError('Please create partition directory %s'
                                           % self.instance_path)
    instance_stat_info = os.stat(self.instance_path)
    permission = oct(stat.S_IMODE(instance_stat_info.st_mode))
    if permission != REQUIRED_COMPUTER_PARTITION_PERMISSION:
      raise WrongPermissionError('Wrong permissions in %s : actual ' \
                                          'permissions are : %s, wanted ' \
                                          'are %s' %
                                          (self.instance_path, permission,
                                            REQUIRED_COMPUTER_PARTITION_PERMISSION))
    os.environ = utils.getCleanEnvironment(pwd.getpwuid(
      instance_stat_info.st_uid).pw_dir)
    # Generates buildout part from template
    # TODO how to fetch the good template? Naming conventions?
    template_location = os.path.join(self.software_path, 'template.cfg')
    config_location = os.path.join(self.instance_path, 'buildout.cfg')
    self.logger.debug("Coping %r to %r" % (template_location, config_location))
    shutil.copy(template_location, config_location)
    # fill generated buildout with additional information
    buildout_text = open(config_location).read()
    buildout_text += '\n\n' + pkg_resources.resource_string(__name__,
        'templates/buildout-tail.cfg.in') % dict(
      computer_id=self.computer_id,
      partition_id=self.partition_id,
      server_url=self.server_url,
      software_release_url=self.software_release_url,
      key_file=self.key_file,
      cert_file=self.cert_file
    )
    open(config_location, 'w').write(buildout_text)
    os.chmod(config_location, 0640)
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
        raise ValueError('More then one bootstrap candidate found.')
      # Reads uid/gid of path, launches buildout with thoses privileges
      bootstrap_file = os.path.abspath(os.path.join(bootstrap_candidate_dir,
        bootstrap_candidate_list[0]))

      file = open(bootstrap_file, 'r')
      line = file.readline()
      file.close()
      invocation_list = []
      if line.startswith('#!'):
        invocation_list = line[2:].split()
      invocation_list.append(bootstrap_file)
      self.logger.debug('Invoking %r in %r' % (' '.join(invocation_list),
        self.instance_path))
      kw = dict()
      if not self.console:
        kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      process_handler = utils.SlapPopen(invocation_list,
        preexec_fn=lambda: utils.dropPrivileges(uid, gid), cwd=self.instance_path,
        env=utils.getCleanEnvironment(pwd.getpwuid(uid).pw_dir), **kw)
      result_std = process_handler.communicate()[0]
      if self.console:
        result_std = 'Please consult messages above.'
      if process_handler.returncode is None or process_handler.returncode != 0:
        message = 'Failed to bootstrap buildout in %r:\n%s\n' % (
            self.instance_path, result_std)
        raise BuildoutFailedError(message)
      buildout_binary = os.path.join(self.instance_path, 'sbin', 'buildout')

    if not os.path.exists(buildout_binary):
      # use own buildout generation
      utils.bootstrapBuildout(self.instance_path, self.buildout,
        ['buildout:bin-directory=%s'% os.path.join(self.instance_path,
        'sbin')], console=self.console)
      buildout_binary = os.path.join(self.instance_path, 'sbin', 'buildout')
    # Launches buildout
    utils.launchBuildout(self.instance_path,
                   buildout_binary, console=self.console)
    # Generates supervisord configuration file from template
    self.logger.info("Generating supervisord config file from template...")
    # check if CP/etc/run exists and it is a directory
    # iterate over each file in CP/etc/run
    # if at least one is not 0750 raise -- partition has something funny
    runner_list = []
    if os.path.exists(self.run_path):
      if os.path.isdir(self.run_path):
        runner_list = os.listdir(self.run_path)
    if len(runner_list) == 0:
      self.logger.warning('No runners found for partition %r' %
          self.partition_id)
      if os.path.exists(self.supervisord_partition_configuration_path):
        os.unlink(self.supervisord_partition_configuration_path)
    else:
      partition_id = self.computer_partition.getId()
      program_partition_template = pkg_resources.resource_stream(__name__,
          'templates/program_partition_supervisord.conf.in').read()
      group_partition_template = pkg_resources.resource_stream(__name__,
          'templates/group_partition_supervisord.conf.in').read()
      partition_supervisor_configuration = group_partition_template % dict(
          instance_id=partition_id,
          program_list=','.join(['_'.join([partition_id, runner])
            for runner in runner_list]))
      for runner in runner_list:
        partition_supervisor_configuration += '\n' + \
            program_partition_template % dict(
          program_id='_'.join([partition_id, runner]),
          program_directory=self.instance_path,
          program_command=os.path.join(self.run_path, runner),
          program_name=runner,
          instance_path=self.instance_path,
          user_id=uid,
          group_id=gid,
          # As supervisord has no environment to inherit setup minimalistic one
          HOME=pwd.getpwuid(uid).pw_dir,
          USER=pwd.getpwuid(uid).pw_name,
        )
      utils.updateFile(self.supervisord_partition_configuration_path,
          partition_supervisor_configuration)
    self.updateSupervisor()

  def start(self):
    """Asks supervisord to start the instance. If this instance is not
    installed, we install it.
    """
    supervisor = self.getSupervisorRPC()
    partition_id = self.computer_partition.getId()
    try:
      supervisor.startProcessGroup(partition_id, False)
    except xmlrpclib.Fault, e:
      if e.faultString.startswith('BAD_NAME:'):
        self.logger.info("Nothing to start on %s..." % \
                         self.computer_partition.getId())
    else:
      self.logger.info("Requested start of %s..." % self.computer_partition.getId())

  def stop(self):
    """Asks supervisord to stop the instance."""
    supervisor = self.getSupervisorRPC()
    partition_id = self.computer_partition.getId()
    try:
      supervisor.stopProcessGroup(partition_id, False)
    except xmlrpclib.Fault, e:
      if e.faultString.startswith('BAD_NAME:'):
        self.logger.info('Partition %s not known in supervisord, ignoring' % partition_id)
    else:
      self.logger.info("Requested stop of %s..." % self.computer_partition.getId())

  def destroy(self):
    """Destroys the partition and makes it available for subsequent use."
    """
    self.logger.info("Destroying Computer Partition %s..." \
        % self.computer_partition.getId())
    # Gets actual buildout binary
    buildout_binary = os.path.join(self.instance_path, 'sbin', 'buildout')
    if not os.path.exists(buildout_binary):
      buildout_binary = os.path.join(self.software_path, 'bin', 'buildout')
    # Launches "destroy" binary if exists
    destroy_executable_location = os.path.join(self.instance_path, 'sbin',
        'destroy')
    if os.path.exists(destroy_executable_location):
      # XXX: we should factorize this code
      uid, gid = None, None
      stat_info = os.stat(self.instance_path)
      uid = stat_info.st_uid
      gid = stat_info.st_gid
      self.logger.debug('Invoking %r' % destroy_executable_location)
      kw = dict()
      if not self.console:
        kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      process_handler = utils.SlapPopen([destroy_executable_location],
        preexec_fn=lambda: utils.dropPrivileges(uid, gid), cwd=self.instance_path,
        env=utils.getCleanEnvironment(pwd.getpwuid(uid).pw_dir), **kw)
      result_std = process_handler.communicate()[0]
      if self.console:
        result_std = 'Please consult messages above'
      if process_handler.returncode is None or process_handler.returncode != 0:
        message = 'Failed to destroy Computer Partition in %r:\n%s\n' % (
            self.instance_path, result_std)
        raise subprocess.CalledProcessError(message)
    # Manually cleans what remains
    try:
      for f in [self.key_file, self.cert_file]:
        if f:
          if os.path.exists(f):
            os.unlink(f)
      for root, dirs, file_list in os.walk(self.instance_path):
        for directory in dirs:
          shutil.rmtree(os.path.join(self.instance_path, directory))
        for file in file_list:
          os.remove(os.path.join(self.instance_path, file))
        if os.path.exists(self.supervisord_partition_configuration_path):
          os.remove(self.supervisord_partition_configuration_path)
        self.updateSupervisor()
    except IOError as error:
      error_string = "I/O error while freeing partition (%s): %s" \
                     % (self.instance_path, error)
      raise IOError(error_string)

  def fetchInformations(self):
    """Fetch usage informations with buildout, returns it.
    """
    raise NotImplementedError

  def getSupervisorRPC(self):
    return getSupervisorRPC(self.supervisord_socket)

  def updateSupervisor(self):
    """Forces supervisord to reload its configuration"""
    # Note: This method shall wait for results from supervisord
    #       In future it will be not needed, as update command
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

