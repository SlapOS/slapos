##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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
import os
import shutil
from slapos.recipe.librecipe import GenericSlapRecipe
import shutil
import subprocess
import sys

class Recipe(GenericSlapRecipe):
  def _install(self):
    path_list = []
    accords_location = self.buildout['accordsdirectory']['accords']

    parameter_dict = dict(
        userid=self.options['userid'],
        tenantname=self.options['tenantname'],
        password=self.options['password'],
        domain=self.options['domain'],
        openstack_url=self.options['openstack_url'],
        python_location=sys.executable,
        accords_location=accords_location,
        manifest_name=self.options['manifest-name'],
        # XXX this is workaround
        accords_lib_directory=self.options['accords_lib_directory'],
        computer_id = self.computer_id,
        computer_partition_id = self.computer_partition_id,
        server_url = self.server_url,
        software_release_url = self.software_release_url,
        key_file = self.key_file,
        cert_file = self.cert_file,
        path = '%s:%s' % (self.options['accords_bin_directory'],
            os.environ.get('PATH', '')),
    )
    # Generate os-config.xml
    os_config_file = self.createFile(self.options['os-config'],
        self.substituteTemplate(self.getTemplateFilename('os_config.xml.in'),
        parameter_dict))
    path_list.append(os_config_file)

    # Put modified accords configuration file
    accords_configuration_parameter_dict = dict(
        listen_ip = self.options['listen-ip']
    )
    accords_configuration_file_location = self.createFile(
        self.options['accords-configuration-file'],
        self.substituteTemplate(self.getTemplateFilename('accords.ini.in'),
        accords_configuration_parameter_dict))
    path_list.append(accords_configuration_file_location)

    # XXX is it dangerous?
    security_path = os.path.join(accords_location, 'security')
    if os.path.exists(security_path):
      shutil.rmtree(security_path)

    # Initiate configuration
    subprocess.check_call('./accords-config',
                          cwd=accords_location
    )

    # Generate manifest
    manifest_origin_location = self.options['manifest-source']
    manifest_location = self.options['manifest-destination']

    shutil.copy(manifest_origin_location, manifest_location)
    path_list.append(manifest_location)

    # Generate wrapper
    wrapper_location = self.createPythonScript(self.options['accords-wrapper'],
        '%s.accords.runAccords' % __name__,
        parameter_dict)
    path_list.append(wrapper_location)

    # Generate helper for debug
    self.createExecutable(
        self.options['testos-wrapper'],
        self.substituteTemplate(self.getTemplateFilename('testos.in'),
            parameter_dict)
    )

    return path_list
