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

import os
import urllib
import urllib2
import pkg_resources
from slapos.recipe.librecipe import BaseSlapRecipe

class SheepDogTestBed(BaseSlapRecipe):

  def _install(self):
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()
    software_type = self.parameter_dict.get('slap_software_type', 'default')
    if software_type is None or software_type == 'RootSoftwareInstance':
      software_type = 'default'
    if "run_%s" % software_type in dir(self) and \
       callable(getattr(self, "run_%s" % software_type)):
      return getattr(self, "run_%s" % software_type)()
    else:
      raise NotImplementedError("Do not support %s" % software_type)

  def run_default(self):
    return self.run_sheepdog_test()

  def run_sheepdog_test(self):
    """ Launch sheepdog test process. """

    sheepdog_test_config = {}
    sheepdog_test_config.update(self.options)
    sheepdog_test_config.update(self.parameter_dict)

    sheepdog_test_config['address'] = self.getGlobalIPv6Address()
    sheepdog_test_config['report_path'] = self.log_directory

    if 'nb_server_max' not in sheepdog_test_config:
      sheepdog_test_config['nb_server_max'] = 0

    if 'nb_tester_max' not in sheepdog_test_config:
      sheepdog_test_config['nb_tester_max'] = 3

    if 'nb_thread' not in sheepdog_test_config:
      sheepdog_test_config['nb_thread'] = 1

    if 'nb_request' not in sheepdog_test_config:
      sheepdog_test_config['nb_request'] = 1000


    sheepdog_test_config['software_release_url'] = self.software_release_url
    sheepdog_test_config['server_url'] = self.server_url
    sheepdog_test_config['key_file'] = self.key_file
    sheepdog_test_config['cert_file'] = self.cert_file
    sheepdog_test_config['computer_id'] = self.computer_id
    sheepdog_test_config['computer_partition_id'] = self.computer_partition_id
    sheepdog_test_config['plugin_name'] = 'sheepdog'

    sheepdog_test_connection = {}
    sheepdog_test_connection['url'] = "http://["+sheepdog_test_config['address']+"]:5000/"
    self.computer_partition.setConnectionDict(sheepdog_test_connection)

    nosqltester_manager_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'nosqltester_manager_run.in'))
    nosqltester_manager_runner_path = self.createRunningWrapper("sheepdog_test_manager",
          self.substituteTemplate(nosqltester_manager_wrapper_template_location, sheepdog_test_config))

    return [nosqltester_manager_runner_path]

  def run_sheepdog_tester(self):
    """ Runs the sheepdog tester. """
    tester_config = {}
    tester_config.update(self.options)
    tester_config.update(self.parameter_dict)

    tester_config['tester_address'] = self.getGlobalIPv6Address()
    tester_config['report_path'] = self.log_directory
    tester_config['binary'] = tester_config['sheepstrike_binary'] + \
                              " -t " + \
                              tester_config['nb_thread'] + " " + \
                              tester_config['nb_request'] #" 1000" " -t 32 1024000"

    tester_connection = {}
    tester_connection['start_url'] = "http://%s:5000/start" % tester_config['tester_address']
    self.computer_partition.setConnectionDict(tester_connection)

    tester_wrapper_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'nosqltester_run.in'))
    tester_runner_path = self.createRunningWrapper("nosqltester",
          self.substituteTemplate(tester_wrapper_template_location, tester_config))

    return [tester_runner_path]

