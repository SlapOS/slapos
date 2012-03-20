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
from slapos import slap
import os
import zc.buildout
import zc.recipe.egg
from hashlib import md5
import stat
import netaddr
import time
import re
import urlparse

# Use to do from slapos.recipe.librecipe import GenericBaseRecipe
from generic import GenericBaseRecipe
from genericslap import GenericSlapRecipe
from filehash import filehash

class BaseSlapRecipe:
  """Base class for all slap.recipe.*"""

  def __init__(self, buildout, name, options):
    """Default initialisation"""
    self.name = name
    options['eggs'] = 'slapos.cookbook'
    self.options = options
    self.logger = logging.getLogger(self.name)
    self.slap = slap.slap()
    self.work_directory = os.path.abspath(buildout['buildout'][
      'directory'])
    self.bin_directory = os.path.join(buildout['buildout'][
      'directory'], 'bin')
    self.data_root_directory = os.path.join(self.work_directory, 'srv')
    self.backup_directory = os.path.join(self.data_root_directory, 'backup')
    self.var_directory = os.path.join(self.work_directory, 'var')
    self.log_directory = os.path.join(self.var_directory, 'log')
    self.run_directory = os.path.join(self.var_directory, 'run')
    self.etc_directory = os.path.join(self.work_directory, 'etc')
    self.tmp_directory = os.path.join(self.work_directory, 'tmp')
    self.wrapper_directory = os.path.join(self.etc_directory, 'run')
    self.wrapper_report_directory = os.path.join(self.etc_directory, 'report')
    self.wrapper_xml_report_directory = os.path.join(self.var_directory,
        'xml_report')
    self.destroy_script_location = os.path.join(self, self.work_directory,
        'sbin', 'destroy')
    self.promise_directory = os.path.join(self.etc_directory, 'promise')

    # default directory structure information
    self.default_directory_list = [
      self.bin_directory, # CP/bin - instance own binaries
      os.path.join(self, self.work_directory, 'sbin'), # CP/sbin - system
       # binaries, not exposed, only CP/sbin/destroy
      self.data_root_directory, # CP/srv - data container
      self.backup_directory, # CP/srv/backup - backup container
      self.etc_directory, # CP/etc - configuration container
      self.wrapper_directory, # CP/etc/run - for wrappers
      self.wrapper_report_directory, # CP/etc/report - for report wrappers
      self.promise_directory, # CP/etc/promise - for promise checking scripts
      self.var_directory, # CP/var - partition "internal" container for logs,
                          # and another metadata
      self.wrapper_xml_report_directory, # CP/var/xml_report - for xml_report wrappers
      self.log_directory, # CP/var/log - log container
      self.run_directory, # CP/var/run - working container - pids, sockets
      self.tmp_directory, # CP/tmp - temporary files
    ]

    # SLAP related information
    slap_connection = buildout['slap_connection']
    self.computer_id = slap_connection['computer_id']
    self.computer_partition_id = slap_connection['partition_id']
    self.server_url = slap_connection['server_url']
    self.software_release_url = slap_connection['software_release_url']
    self.key_file = slap_connection.get('key_file')
    self.cert_file = slap_connection.get('cert_file')

    # setup egg to give possibility to generate scripts
    self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)

    # Hook options
    self._options(options)

    # setup auto uninstall/install
    self._setupAutoInstallUninstall()

  def _setupAutoInstallUninstall(self):
    """By default SlapOS recipes are reinstalled each time"""
    # Note: It is possible to create in future subclass which will do no-op in
    # this method
    self.options['slapos_timestamp'] = str(time.time())

  def _getIpAddress(self, test_method):
    """Internal helper method to fetch ip address"""
    if not 'ip_list' in self.parameter_dict:
      raise AttributeError
    for name, ip in self.parameter_dict['ip_list']:
      if test_method(ip):
        return ip
    raise AttributeError

  def getLocalIPv4Address(self):
    """Returns local IPv4 address available on partition"""
    # XXX: Lack checking for locality of address
    return self._getIpAddress(netaddr.valid_ipv4)

  def getGlobalIPv6Address(self):
    """Returns global IPv6 address available on partition"""
    # XXX: Lack checking for globality of address
    return self._getIpAddress(netaddr.valid_ipv6)

  def createConfigurationFile(self, name, content):
    """Creates named configuration file and returns its path"""
    file_path = os.path.join(self.etc_directory, name)
    self._writeFile(file_path, content)
    self.logger.debug('Created configuration file: %r' % file_path)
    return file_path

  def createRunningWrapper(self, wrapper_name, file_content):
    """Creates named running wrapper and returns its path"""
    wrapper_path = os.path.join(self.wrapper_directory, wrapper_name)
    self._writeExecutable(wrapper_path, file_content)
    return wrapper_path

  def createReportRunningWrapper(self, file_content):
    """Creates report runnig wrapper and returns its path"""
    report_wrapper_path = os.path.join(self.wrapper_report_directory,
        'slapreport')
    self._writeExecutable(report_wrapper_path, file_content)
    return report_wrapper_path

  def substituteTemplate(self, template_location, mapping_dict):
    """Returns template content after substitution"""
    return open(template_location, 'r').read() % mapping_dict

  def _writeExecutable(self, path, content, mode='0700'):
    """Creates file in path with content and sets mode

    If file was created or altered returns true
    Otherwise returns false

    To be used to create executables

    Raises os related errors"""
    return self._writeFile(path, content, mode)

  def _writeFile(self, path, content, mode='0600'):
    """Creates file in path with content and sets mode

    If file was created or altered returns true
    Otherwise returns false

    Raises os related errors"""

    file_altered = False
    if not os.path.exists(path):
      open(path, 'w').write(content)
      file_altered = True
    else:
      new_sum = md5()
      current_sum = md5()
      new_sum.update(content)
      current_sum.update(open(path, 'r').read())
      if new_sum.digest() != current_sum.digest():
        file_altered = True
        open(path, 'w').write(content)

    if oct(stat.S_IMODE(os.stat(path).st_mode)) != mode:
      os.chmod(path, int(mode, 8))
      file_altered = True

    return file_altered

  def createBackupDirectory(self, name, mode='0700'):
    """Creates named directory in self.backup_directory and returns its path"""
    path = os.path.join(self.backup_directory, name)
    self._createDirectory(path, mode)
    return path

  def createDataDirectory(self, name, mode='0700'):
    """Creates named directory in self.data_root_directory and returns its path"""
    path = os.path.join(self.data_root_directory, name)
    self._createDirectory(path, mode)
    return path

  def _createDirectory(self, path, mode='0700'):
    """Creates path directory and sets mode

    If directory was created or its mode was altered returns true
    Otherwise returns false

    Raises os related errors"""
    directory_altered = False
    if not os.path.exists(path):
      os.mkdir(path, int(mode, 8))
      directory_altered = True
    if not os.path.isdir(path):
      raise zc.buildout.UserError('Path %r exists, but it is not directory'
          % path)
    if oct(stat.S_IMODE(os.stat(path).st_mode)) != mode:
      os.chmod(path, int(mode, 8))
      directory_altered = True
    if directory_altered:
      self.logger.debug('Created directory %r with permission %r' % (path, mode))
    return directory_altered

  def _createDefaultDirectoryStructure(self):
    for directory in self.default_directory_list:
      self._createDirectory(directory)

  def generatePassword(self, len=32):
    """Generates password. Shall be secured, until then all are insecure"""
    return 'insecure'

  def install(self):
    self.slap.initializeConnection(self.server_url, self.key_file,
        self.cert_file)
    self.computer_partition = self.slap.registerComputerPartition(
      self.computer_id,
      self.computer_partition_id)
    self.request = self.computer_partition.request
    self.setConnectionDict = self.computer_partition.setConnectionDict
    self._createDefaultDirectoryStructure()
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()

    # call children part of install
    path_list = self._install()

    return path_list

  update = install

  def _install(self):
    """Hook which shall be implemented in children class"""
    raise NotImplementedError('Shall be implemented by subclass')

  def _options(self, options):
    """Hook which can be implemented in children class"""
    pass

  def createPromiseWrapper(self, promise_name, file_content):
    """Create a promise wrapper.

    This wrapper aim to check if the software release is doing its job.

    Return the promise file path.
    """
    promise_path = os.path.join(self.promise_directory, promise_name)
    self._writeExecutable(promise_path, file_content)
    return promise_path

  def setConnectionUrl(self, *args, **kwargs):
    url = self._unparseUrl(*args, **kwargs)
    self.setConnectionDict(dict(url=url))

  def _unparseUrl(self, scheme, host, path='', params='', query='',
                  fragment='', port=None, auth=None):
    """Join a url with auth, host, and port.

    * auth can be either a login string or a tuple (login, password).
    * if the host is an ipv6 address, brackets will be added to surround it.

    """
    # XXX-Antoine: I didn't find any standard module to join an url with
    # login, password, ipv6 host and port.
    # So instead of copy and past in every recipe I factorized it right here.
    netloc = ''
    if auth is not None:
      auth = tuple(auth)
      netloc = str(auth[0]) # Login
      if len(auth) > 1:
        netloc += ':%s' % auth[1] # Password
      netloc += '@'

    # host is an ipv6 address whithout brackets
    if ':' in host and not re.match(r'^\[.*\]$', host):
      netloc += '[%s]' % host
    else:
      netloc += str(host)

    if port is not None:
      netloc += ':%s' % port

    url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

    return url

