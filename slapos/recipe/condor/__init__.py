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
from slapos.recipe.librecipe import GenericBaseRecipe
import os
import subprocess
import zc.buildout
import filecmp
import urlparse
import shutil
import re
import json

class Recipe(GenericBaseRecipe):
  """Deploy a fully operational condor architecture."""

  def __init__(self, buildout, name, options):
    self.environ = {}
    self.role = ''
    environment_section = options.get('environment-section', '').strip()
    if environment_section and environment_section in buildout:
      # Use environment variables from the designated config section.
      self.environ.update(buildout[environment_section])
    for variable in options.get('environment', '').splitlines():
      if variable.strip():
        try:
          key, value = variable.split('=', 1)
          self.environ[key.strip()] = value
        except ValueError:
          raise zc.buildout.UserError('Invalid environment variable definition: %s', variable)
    # Extrapolate the environment variables using values from the current
    # environment.
    for key in self.environ:
      self.environ[key] = self.environ[key] % os.environ
    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def _options(self, options):
    #Path of condor compiled package
    self.package = options['package'].strip()
    self.rootdir = options['rootdirectory'].strip()
    #Other condor dependances
    self.javabin = options['java-bin'].strip()
    self.dash = options['dash'].strip()
    #Directory to deploy condor
    self.prefix = options['rootdirectory'].strip()
    self.localdir = options['local-dir'].strip()
    self.wrapperdir = options['wrapper-dir'].strip()
    self.wrapper_bin = options['bin'].strip()
    self.wrapper_sbin = options['sbin'].strip()

    self.diskspace = options['disk-space'].strip()
    self.ipv6 = options['ip'].strip()
    self.condor_host = options['condor_host'].strip()
    self.collector_name = options['collector_name'].strip()
    self.host_list = self.options.get('allowed-write', '*')
    self.email = self.options.get('admin-email', "root@$(FULL_HOSTNAME)")

  def install(self):
    path_list = []
    #get UID and GID for current slapuser
    stat_info = os.stat(self.rootdir)
    slapuser = str(stat_info.st_uid)+"."+str(stat_info.st_gid)
    domain_name = 'slapos%s.com' % stat_info.st_uid

    #Configure condor
    configure_script = os.path.join(self.package, 'condor_configure')
    install_args = [configure_script, '--install='+self.package,
              '--prefix='+self.prefix, '--overwrite', '--verbose',
              '--local-dir='+self.localdir] #--ignore-missing-libs
    if self.options['machine-role'].strip() == "manager":
      self.role = "manager,submit"
    elif self.options['machine-role'].strip() == "worker":
      self.role = "execute"
      install_args += ['--central-manager='+self.condor_host]
    install_args += ['--type='+self.role]
    configure = subprocess.Popen(install_args, env=self.environ,
                  stdout=subprocess.PIPE)
    configure.communicate()[0]
    if configure.returncode is None or configure.returncode != 0:
      return path_list

    #Generate condor_configure file
    condor_config = os.path.join(self.rootdir, 'etc/condor_config')
    config_local = os.path.join(self.localdir, 'condor_config.local')
    condor_configure = dict(condor_host=self.condor_host, releasedir=self.prefix,
                  localdir=self.localdir, config_local=config_local,
                  slapuser=slapuser, ipv6=self.ipv6,
                  diskspace=self.diskspace, javabin=self.javabin,
                  host_list=self.host_list, collector_name=self.collector_name,
                  email=self.email, domain_name=domain_name)
    destination = os.path.join(condor_config)
    config = self.createFile(destination,
      self.substituteTemplate(self.getTemplateFilename('condor_config.generic'),
      condor_configure))
    path_list.append(config)

    #Search if is needed to update condor_config.local file
    find = re.search('NETWORK_INTERFACE[\s]*=[\s]*(%s)' % self.ipv6,
                                              open(config_local, 'r').read())
    if not find:
      #update condor_config.local
      with open(config_local, 'a') as f:
        if self.role == "execute":
          f.write("\nSTART = TRUE")
        f.write("\nCOLLECTOR_NAME = %s\n \nNETWORK_INTERFACE=%s" %
                  (self.collector_name, self.ipv6))

    #create condor binary launcher for slapos
    if not os.path.exists(self.wrapper_bin):
      os.makedirs(self.wrapper_bin, int('0744', 8))
    if not os.path.exists(self.wrapper_sbin):
      os.makedirs(self.wrapper_sbin, int('0744', 8))
    #generate script for each file in prefix/bin
    for binary in os.listdir(self.prefix+'/bin'):
      wrapper_location = os.path.join(self.wrapper_bin, binary)
      current_exe = os.path.join(self.prefix, 'bin', binary)
      wrapper = open(wrapper_location, 'w')
      content = """#!%s
      export LD_LIBRARY_PATH=%s
      export PATH=%s
      export CONDOR_CONFIG=%s
      export CONDOR_LOCATION=%s
      export CONDOR_IDS=%s
      export HOME=%s
      export HOSTNAME=%s
      exec %s $*""" % (self.dash,
              self.environ['LD_LIBRARY_PATH'], self.environ['PATH'],
              condor_config, self.prefix, slapuser, self.environ['HOME'],
              self.environ['HOSTNAME'], current_exe)
      wrapper.write(content)
      wrapper.close()
      path_list.append(wrapper_location)
      os.chmod(wrapper_location, 0744)

    #generate script for each file in prefix/sbin
    for binary in os.listdir(self.prefix+'/sbin'):
      wrapper_location = os.path.join(self.wrapper_sbin, binary)
      current_exe = os.path.join(self.prefix, 'sbin', binary)
      wrapper = open(wrapper_location, 'w')
      content = """#!%s
      export LD_LIBRARY_PATH=%s
      export PATH=%s
      export CONDOR_CONFIG=%s
      export CONDOR_LOCATION=%s
      export CONDOR_IDS=%s
      export HOME=%s
      export HOSTNAME=%s
      exec %s $*""" % (self.dash,
              self.environ['LD_LIBRARY_PATH'], self.environ['PATH'],
              condor_config, self.prefix, slapuser, self.environ['HOME'],
              self.environ['HOSTNAME'], current_exe)
      wrapper.write(content)
      wrapper.close()
      path_list.append(wrapper_location)
      os.chmod(wrapper_location, 0744)

    #generate script for start condor
    start_condor = os.path.join(self.wrapperdir, 'start_condor')
    start_bin = os.path.join(self.wrapper_sbin, 'condor_master')
    condor_reconfig = os.path.join(self.wrapper_sbin, 'condor_reconfig')
    wrapper = self.createPythonScript(start_condor,
        '%s.configure.condorStart' % __name__,
        dict(start_bin=start_bin, condor_reconfig=condor_reconfig)
    )
    path_list.append(wrapper)
    return path_list

class AppSubmit(GenericBaseRecipe):
  """Submit a condor job into an existing Condor master instance"""

  def download(self, url, filename=None, md5sum=None):
    cache = os.path.join(self.options['rootdirectory'].strip(), 'tmp')
    if not os.path.exists(cache):
      os.mkdir(cache)
    downloader = zc.buildout.download.Download(self.buildout['buildout'],
                    hash_name=True, cache=cache)
    path, _ = downloader(url, md5sum)
    if filename:
      name = os.path.join(cache, filename)
      os.rename(path, name)
      return name
    return path

  def copy_file(self, source, dest):
    """"Copy file with source to dest with auto replace
        return True if file has been copied and dest ha been replaced
    """
    result = False
    if source and os.path.exists(source):
      if os.path.exists(dest):
        if filecmp.cmp(dest, source):
          return False
        os.unlink(dest)
      result = True
      shutil.copy(source, dest)
    return result

  def getFiles(self):
    """This is used to download app files if necessary and update options values"""
    app_list = json.loads(self.options['condor-app-list'])
    if not app_list:
      return None
    for app in app_list:
      if app_list[app].get('files', None):
        file_list = app_list[app]['files']
        for file in file_list:
          if file and (file.startswith('http') or file.startswith('ftp')):
            file_list[file] = self.download(file_list[file])
          os.chmod(file_list[file], 0600)
      else:
        app_list[app]['files'] = {}

      executable = app_list[app].get('executable', '')
      if executable and (executable.startswith('http') or executable.startswith('ftp')):
        app_list[app]['executable'] = self.download(executable,
                                      app_list[app]['executable-name'])
        os.chmod(app_list[app]['executable-name'], 0700)
      submit_file = app_list[app].get('description-file', '')
      if submit_file and (submit_file.startswith('http') or submit_file.startswith('ftp')):
        app_list[app]['description-file'] = self.download(submit_file, 'submit')
        os.chmod(app_list[app]['description-file'], 0600)

    return app_list

  def install(self):
    path_list = []
    #check if curent condor instance is an condor master
    if self.options['machine-role'].strip() != "manager":
      raise Exception("Cannot submit a job to Condor worker instance")

    #Setup directory
    jobdir = self.options['job-dir'].strip()
    if not os.path.exists(jobdir):
      os.mkdir(jobdir)
    app_list = self.getFiles()
    for appname in app_list:
      appdir = os.path.join(jobdir, appname)
      if not os.path.exists(appdir):
        os.mkdir(appdir)
      submitfile = os.path.join(appdir, 'submit')

      self.copy_file(app_list[appname]['executable'],
                    os.path.join(appdir, app_list[appname]['executable-name'])
      )
      install = self.copy_file(app_list[appname]['description-file'], submitfile)
      sig_install = os.path.join(appdir, '.install')
      if install:
        with open(sig_install, 'w') as f:
          f.write('to_install')
      for file in app_list[appname]['files']:
        destination = os.path.join(appdir, file)
        if os.path.exists(destination):
          os.unlink(destination)
        os.symlink(app_list[appname]['files'][file], destination)
      #generate wrapper for submitting job
      condor_submit = os.path.join(self.options['bin'].strip(), 'condor_submit')
      parameter = dict(submit=condor_submit, sig_install=sig_install,
                      submit_file='submit',
                      appname=appname, appdir=appdir)
      submit_job = self.createPythonScript(
        os.path.join(self.options['wrapper-dir'].strip(), appname),
        '%s.configure.submitJob' % __name__, parameter
      )
      path_list.append(submit_job)
    return path_list