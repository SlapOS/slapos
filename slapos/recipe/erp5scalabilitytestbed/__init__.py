##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING:  This  program as  such  is intended  to  be  used by  professional
# programmers  who take the  whole responsibility  of assessing  all potential
# consequences resulting from its eventual inadequacies and bugs End users who
# are  looking for  a  ready-to-use solution  with  commercial guarantees  and
# support are strongly adviced to contract a Free Software Service Company
#
# This  program is Free  Software; you  can redistribute  it and/or  modify it
# under the terms  of the GNU General Public License as  published by the Free
# Software Foundation;  either version 3 of  the License, or  (at your option)
# any later version.
#
# This program is distributed in the  hope that it will be useful, but WITHOUT
# ANY  WARRANTY;  without even  the  implied  warranty  of MERCHANTABILITY  or
# FITNESS FOR  A PARTICULAR PURPOSE.  See  the GNU General  Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################

import os
import pkg_resources
from slapos.recipe.librecipe import BaseSlapRecipe

class Recipe(BaseSlapRecipe):
  def _install(self):
    self.parameter_dict = self.computer_partition.getInstanceParameterDict()
    software_type = self.parameter_dict.get('slap_software_type', 'default')
    if software_type is None or software_type == 'RootSoftwareInstance':
      software_type = 'erp5_scalability_cloud'
    if "run_%s" % software_type in dir(self) and \
       callable(getattr(self, "run_%s" % software_type)):
      return getattr(self, "run_%s" % software_type)()
    else:
      raise NotImplementedError("Do not support %s" % software_type)

  def run_erp5_scalability_cloud(self):
    config = {}
    config.update(self.options)
    config.update(self.parameter_dict)

    config['address'] = self.getGlobalIPv6Address()
    config['report_path'] = self.log_directory
    config.setdefault('user_range_increment', 1)
    config['software_release_url'] = self.software_release_url
    config['server_url'] = self.server_url
    config['key_file'] = self.key_file
    config['cert_file'] = self.cert_file
    config['computer_id'] = self.computer_id
    config['computer_partition_id'] = self.computer_partition_id
    config['plugin_name'] = 'erp5'

    if ',' in config['nb_users']:
      config['nb_tester_init'] = config['nb_users'].split(',')[0]
      config['nb_tester_max'] = config['nb_users'].split(',')[1]
    else:
      config['nb_tester_init'] = config['nb_users']
      config['nb_tester_max'] = config['nb_users']

    connection = {}
    connection['url'] = 'http://['+config['address']+']:5000/'
    connection['erp5_url'] = config['erp5_url']
    connection['repeat'] = config['repeat']
    connection['nb_users'] = config['nb_users']
    connection['benchmark_suites'] = config['benchmark_suites']
    connection['erp5_publish_url'] = config.get('erp5_publish_url', '')
    connection['erp5_publish_project'] = config.get('erp5_publish_project', '')

    self.computer_partition.setConnectionDict(connection)

    nosqltester_manager_wrapper_template_location = pkg_resources.resource_filename(
      __name__, os.path.join('template', 'erp5tester_manager_run.in'))

    nosqltester_manager_runner_path = self.createRunningWrapper("erp5tester_manager",
          self.substituteTemplate(nosqltester_manager_wrapper_template_location, config))

    return [nosqltester_manager_runner_path]

  def run_erp5_tester(self):
    tester_config = {}
    tester_config.update(self.options)
    tester_config.update(self.parameter_dict)

    tester_config['tester_address'] = self.getGlobalIPv6Address()
    tester_config['report_path'] = self.log_directory
    tester_config['filename_prefix'] = '%s-%s' % (self.computer_id,
                                                  self.computer_partition_id)

    tester_connection = {'url': 'http://[%s]:5000/' % \
                           tester_config['tester_address']}

    self.computer_partition.setConnectionDict(tester_connection)

    tester_wrapper_template_location = pkg_resources.resource_filename(
      __name__, os.path.join('template', 'nosqltester_run.in'))

    tester_runner_path = self.createRunningWrapper("nosqltester",
          self.substituteTemplate(tester_wrapper_template_location, tester_config))

    return [tester_runner_path]
