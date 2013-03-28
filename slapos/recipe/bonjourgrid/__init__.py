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
import pwd
import signal
import zc.buildout

class Recipe(GenericBaseRecipe):
  """Deploy a fully operational BonjourGrid Master architecture."""


  def install(self):
    path_list = []
    condor_wrapper = self.options['condor-wrapper'].strip()
    boinc_wrapper = self.options['boinc-wrapper'].strip()
    startCondor = startBoinc = False
    condor_wrapper_list = []
    boinc_wrapper_list = []
    for file in os.listdir(condor_wrapper):
      condor_wrapper_list.append(os.path.join(condor_wrapper, file))
    for file in os.listdir(boinc_wrapper):
      boinc_wrapper_list.append(os.path.join(boinc_wrapper, file))

    type = self.options['type'].strip()
    if type == "condor":
      startCondor = True
      project = self.options['condor_host'].strip()
    if type == "boinc":
      project = self.options['url-boinc'].strip()
      startBoinc = True

    #Generate BOINC/Condor launcher script
    grid_wrapper = self.options['boinc_condor_wrapper'].strip()
    parameters = dict(startCondor=startCondor, startBoinc=startBoinc,
                      bg_base=self.options['work_dir'].strip(),
                      condor_wrapper_list=condor_wrapper_list,
                      boinc_wrapper_list=boinc_wrapper_list)
    bonjourGrid_wrapper = self.createPythonScript(grid_wrapper,
        '%s.configure.launchScript' % __name__,
        parameters
    )
    path_list.append(bonjourGrid_wrapper)

    #Generate wrapper for BonjourGrid Master
    bonjourgrid_master = self.options['master_script'].strip()
    python = self.options['python-bin'].strip()
    bg_wrapper = self.options['wrapper'].strip()
    log = self.options['log_file'].strip()
    pid_file = self.options['pid_file'].strip()
    wrapper = self.createPythonScript(bg_wrapper,
        'slapos.recipe.librecipe.execute.execute',
        ([python, bonjourgrid_master, '--log_file', log,
          '--pid_file', pid_file,
          '--master_wrapper', grid_wrapper,
          '--directory', self.options['work_dir'].strip(),
          '--server', self.options['redis-url'].strip(),
          '--port', self.options['redis-port'].strip(),
          '--num_workers', self.options['nworkers'].strip(),
        ])
    )
    path_list.append(wrapper)


    #generate Computer information file
    config_info_file = os.path.join(self.options['work_dir'].strip(),
                                'machineinfo.sh')
    config_info = self.createFile(config_info_file,
      self.substituteTemplate(self.getTemplateFilename('machineinfo.sh.in'),
      dict(ip_address=self.options['ipv6'].strip(),
            project=project,
            middleware=type)))
    os.chmod(config_info_file, 0744)
    path_list.append(config_info)

  update = install

class Client(GenericBaseRecipe):

  def install(self):
    path_list = []
    boinc_script = self.options['boinc_script'].strip()
    condor_script = self.options['condor_script'].strip()

    #Generate wrapper for BonjourGrid Worker
    bonjourgrid_client = self.options['client_script'].strip()
    python = self.options['python-bin'].strip()
    bg_wrapper = self.options['wrapper'].strip()
    log = self.options['log_file'].strip()
    pid_file = self.options['pid_file'].strip()
    wrapper = self.createPythonScript(bg_wrapper,
        'slapos.recipe.librecipe.execute.execute',
        ([python, bonjourgrid_client, '--log_file', log,
          '--pid_file', pid_file,
          '--boinc_wrapper', boinc_script,
          '--condor_wrapper', condor_script,
          '--directory', self.options['work_dir'].strip(),
          '--install_directory', self.options['install_dir'].strip(),
          '--server', self.options['redis-url'].strip(),
          '--port', self.options['redis-port'].strip(),
        ])
    )
    path_list.append(wrapper)

    #generate BOINC and Condor configure script for bonjourgrid
    boinc_wrapper = self.createPythonScript(boinc_script,
        '%s.boinc.runBoinc' % __name__,
        dict(ipv6=self.options['ipv6'].strip(),
            email=self.options['email'].strip(),
            boinc_wrapper=self.options['boinc_wrapper'].strip(),
            boinc_cmd=self.options['boinc_cmd'].strip(),
            boinc_rpc_port=self.options['boinc_rpc_port'],
            boinc_install_dir=self.options['boinc_install_dir'].strip(),
            boinc_passwd=self.options['boinc_passwd'].strip(),
            account_name=self.options['account_name'].strip(),
            account_passwd=self.options['account_passwd'].strip(),
        )
    )
    path_list.append(boinc_wrapper)
    condor_wrapper = self.createPythonScript(condor_script,
        '%s.condor.runCondor' % __name__,
        dict(ipv6=self.options['ipv6'].strip(),
            condor_bin=self.options['condor_bin'].strip(),
            condor_sbin=self.options['condor_sbin'].strip(),
            condor_wrapper=self.options['condor_wrapper'].strip(),
            condor_config=self.options['condor_config'].strip(),
            condor_config_local=self.options['condor_config_local'].strip(),
        )
    )
    path_list.append(condor_wrapper)

