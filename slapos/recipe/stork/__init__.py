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
    #Path of stork compiled package
    self.package = options['package'].strip()
    self.rootdir = options['rootdirectory'].strip()
    #Other stork dependances
    self.javabin = options['java-bin'].strip()
    self.dash = options['dash'].strip()
    #Directory to deploy stork
    self.prefix = options['rootdirectory'].strip()
    self.wrapper_bin = options['bin'].strip()
    self.wrapper_sbin = options['sbin'].strip()
    self.wrapper_log= options['log'].strip()
    self.wrapper_tmp= options['tmp'].strip()
    self.ipv4 = options['ipv4'].strip()
    self.stork_host = options['stork_host'].strip()
    self.stork_port = options['stork_port'].strip()
  def install(self):
    path_list = []
    #get UID and GID for current slapuser
    stat_info = os.stat(self.rootdir)
    slapuser = str(stat_info.st_uid)+"."+str(stat_info.st_gid)
    domain_name = 'slapos%s.com' % stat_info.st_uid


    #Generate stork_mabroukconfig file
    stork_config = os.path.join(self.rootdir, 'etc/stork_config')
    stork_configure = dict(stork_host=self.stork_host, releasedir=self.prefix,
                  storkpackage=self.package,
                  slapuser=slapuser, ipv4=self.ipv4,
                  port=self.stork_port)
    destination = os.path.join(stork_config)
     # case 1: client and server in the same instance
    if (self.options['machine-role'] == "client") and (self.options['stork_server']=='local'):
     config = self.createFile(destination,
      self.substituteTemplate(self.getTemplateFilename('stork_config.generic'),
      stork_configure))
     path_list.append(config)
    #case 2: client and server in different instances (the server may b a remote host)
    else:
     config = self.createFile(destination,
      self.substituteTemplate(self.getTemplateFilename('remote_stork_config.generic'),
      stork_configure))
     path_list.append(config)


    #create stork binary launcher for slapos
    if not os.path.exists(self.wrapper_bin):
      os.makedirs(self.wrapper_bin, int('0700', 8))
    if not os.path.exists(self.wrapper_sbin):
      os.makedirs(self.wrapper_sbin, int('0700', 8))
    if not os.path.exists(self.wrapper_log):
      os.makedirs(self.wrapper_log, int('0700', 8))
    if not os.path.exists(self.wrapper_tmp):
      os.makedirs(self.wrapper_tmp, int('0700', 8))
    #generate script for each file in prefix/bin
    for binary in os.listdir(self.package+'/bin'):
      wrapper_location = os.path.join(self.wrapper_bin, binary)
      current_exe = os.path.join(self.package, 'bin', binary)
      wrapper = open(wrapper_location, 'w')
      content = """#!%s
      export LD_LIBRARY_PATH=%s
      export PATH=%s
      export STORK_CONFIG=%s
      export STORK_HOME=%s
      export STORK_IDS=%s
      export HOSTNAME=%s
      exec %s $*""" % (self.dash,
              self.environ['LD_LIBRARY_PATH'], self.environ['PATH'],
              stork_config, self.prefix, slapuser,
              self.environ['HOSTNAME'], current_exe)
      wrapper.write(content)
      wrapper.close()
      path_list.append(wrapper_location)
      os.chmod(wrapper_location, 0700)

    #generate script for each file in prefix/sbin
    for binary in os.listdir(self.package+'/sbin'):
      wrapper_location = os.path.join(self.wrapper_sbin, binary)
      current_exe = os.path.join(self.package, 'sbin', binary)
      wrapper = open(wrapper_location, 'w')
      content = """#!%s
      export LD_LIBRARY_PATH=%s
      export PATH=%s
      export STORK_CONFIG=%s
      export STORK_HOME=%s
      export STORK_IDS=%s
      export HOSTNAME=%s
      exec %s $*""" % (self.dash,
              self.environ['LD_LIBRARY_PATH'], self.environ['PATH'],
              stork_config, self.prefix, slapuser,
              self.environ['HOSTNAME'], current_exe)
      wrapper.write(content)
      wrapper.close()
      path_list.append(wrapper_location)
      os.chmod(wrapper_location, 0700)

    #generate script for start stork
    if self.options['stork_server']=='local':
     start_bin = os.path.join(self.wrapper_sbin, 'stork_server')
     wrapper = self.createPythonScript(self.options['wrapper-path'].strip(),
        '%s.configure.storkStart' % __name__,
        dict(start_bin=start_bin,
            port=self.stork_port,
            configfile=self.rootdir+'/etc/stork_config',
            pid=self.options['pid']))
     path_list.append(wrapper)
    return path_list

class AppSubmit(GenericBaseRecipe):
  """Submit a stork job into an existing Stork server instance"""

  def install(self):
    path_list = []
    download_dest_list = dict()
    #check if curent stork instance is an stork server
    if self.options['machine-role'].strip() == "server":
      #raise Exception("Cannot submit a job to stork client instance")
      print 'Cannot submit a job to stork client instance'
      return path_list

    #Setup directory
    datadir = self.options['data-dir'].strip()
    dest_url = self.options['dest_url'].strip()
    source_url_list = self.options['json_src_url'].strip()
    submitfile = os.path.join(datadir, 'submit-dap')
    if self.options['dest_url']=='local':
      dest_url = 'file:'+datadir
    
    stork_submit = os.path.join(self.options['bin'].strip(), 'stork_submit')
    file_list = '{}'
    if str(self.options.get('src_from_file')).lower() in ['y', 'yes', '1', 'true']:
      if os.path.exists(source_url_list):
        with open(source_url_list, 'r') as file_source:
          file_list = json.loads(file_source.read())
    else:
      file_list = json.loads(source_url_list)
    with open(submitfile, 'w') as stork_file:
      # XXX - Simply, we don't want to download file twice with stork,
      #       skip file if it already exists at dest_url (only for file:path)
      for filename in file_list:
        download_name = filename
        if dest_url.startswith('file:'):
          destination = os.path.join(dest_url.replace('file:', ''), filename)
          if os.path.exists(destination+'_part') or os.path.exists(destination):
            continue
          download_dest_list[filename] = destination
          download_name = filename + '_part'
        stork_file.write("""[
src_url="%s";
dest_url="%s/%s";
err = "%s.err";
output = "%s.out";
dap_type = "transfer";
set_permission = "600" ;
]

""" % (file_list[filename], dest_url, download_name, filename, filename)
          )
  
    parameter = dict(submit=stork_submit,
                    submit_file=submitfile,
                    stork_server=self.options['ipv4'].strip(),
                    server_port=self.options['stork_port'].strip(),
                    datadir=datadir)
    submit_job = self.createPythonScript(
      self.options['wrapper-path'].strip(),
      '%s.configure.submitJob' % __name__, parameter
    )
    path_list.append(submit_job)
    
    check_job = self.createPythonScript(
      self.options['wrapper-check'].strip(),
      '%s.configure.checkDownloadStatus' % __name__,
      dict(dest_list=download_dest_list, cwd=self.options['log'])
    )
    path_list.append(check_job)
    
    return path_list