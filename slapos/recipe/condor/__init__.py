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

class Recipe(GenericBaseRecipe):
  """Deploy a fully operational condor architecture."""

  def _options(self, options):
    #Path of condor compiled package
    self.package = options['package'].strip()
    self.rootdir = options['rootdirectory'].strip()
    #Other condor dependances
    self.perlbin = options['perl-bin'].strip()
    self.javabin = options['java-bin'].strip()
    self.dash = options['dash'].strip()
    #Directory to deploy condor
    self.prefix = options['rootdirectory'].strip()
    self.localdir = options['local-dir'].strip()
    self.config_wrapper = options['config_wrapper'].strip()
    self.wrapper_bin = options['bin'].strip()
    self.wrapper_sbin = options['sbin'].strip()

    self.diskspace = options['disk-space'].strip()
    self.ipv6 = options['ip'].strip()
    self.condor_host = options['condor_host'].strip()
    self.domain = options['domain'].strip()
    self.collector = options['collector_name'].strip()
    self.linkdir = options['linkdir'].strip()
    self.path = options['path'].strip()
    if options['machine-role'].strip() == "manager":
      self.role = "manager,submit"
    elif options['machine-role'].strip() == "worker":
      self.role = "submit,execute"

  def install(self):
    path_list = []
    #get UID and GID for current slapuser
    stat_info = os.stat(self.rootdir)
    slapuser = str(stat_info.st_uid)+"."+str(stat_info.st_gid)

    #Configure condor
    environment = os.environ.copy()
    environment['PATH'] = os.path.dirname(self.perlbin) + ':' + environment['PATH']
    environment['LD_LIBRARY_PATH'] = os.path.dirname(self.perlbin) + ':' + os.environ['PATH']
    environment['HOME'] = self.localdir
    environment['HOSTNAME'] = self.condor_host

    configure_script = os.path.join(self.package, 'condor_configure')
    install_args = [configure_script, '--install='+self.package,
              '--prefix='+self.prefix, '--overwrite',
              '--local-dir='+self.localdir, '--type='+self.role]
    configure = subprocess.Popen(install_args, env=environment,
                  stdout=subprocess.PIPE)
    configure.wait()

    #Generate condor_configure file
    condor_config = os.path.join(self.rootdir, 'etc/condor_config')
    config_local = os.path.join(self.localdir, 'condor_config.local')
    condor_configure = dict(condor_host=self.condor_host, releasedir=self.prefix,
                  localdir=self.localdir, config_local=config_local,
                  slapuser=slapuser, domain=self.domain, ipv6=self.ipv6,
                  diskspace=self.diskspace, javabin=self.javabin)
    destination = os.path.join(condor_config)
    config = self.createFile(destination,
      self.substituteTemplate(self.getTemplateFilename('condor_config.generic'),
      condor_configure))
    path_list.append(config)

    #Update condor_configure.local file
    #config_local_path = os.path.join(self.localdir, 'condor_config.local')

    #create condor binary launcher for slapos
    if not os.path.exists(self.wrapper_bin):
      os.makedirs(self.wrapper_bin, int('0744', 8))
    if not os.path.exists(self.wrapper_sbin):
      os.makedirs(self.wrapper_sbin, int('0744', 8))
    #self.path = wrapper_bin+":"+wrapper_sbin+":"+self.path
    #generate script for each file in prefix/bin
    for binary in os.listdir(self.prefix+'/bin'):
      wrapper_location = os.path.join(self.wrapper_bin, binary)
      current_exe = os.path.join(self.prefix, 'bin', binary)
      wrapper = open(wrapper_location, 'w')
      content = """#!%s
      cd %s
      export LD_LIBRARY_PATH=%s
      export PATH=%s
      export CONDOR_CONFIG=%s
      export CONDOR_LOCATION=%s
      export CONDOR_IDS=%s
      export HOME=%s
      export HOSTNAME=%s
      exec %s $*""" % (self.dash, self.wrapper_bin, self.linkdir, self.path,
              condor_config, self.prefix, slapuser, self.localdir,
              self.condor_host, current_exe)
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
      cd %s
      export LD_LIBRARY_PATH=%s
      export PATH=%s
      export CONDOR_CONFIG=%s
      export CONDOR_LOCATION=%s
      export CONDOR_IDS=%s
      export HOME=%s
      export HOSTNAME=%s
      exec %s $*""" % (self.dash, self.wrapper_sbin, self.linkdir, self.path,
              condor_config, self.prefix, slapuser, self.localdir,
              self.condor_host, current_exe)
      wrapper.write(content)
      wrapper.close()
      path_list.append(wrapper_location)
      os.chmod(wrapper_location, 0744)
    return path_list
