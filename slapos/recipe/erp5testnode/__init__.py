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
from slapos.recipe.librecipe import BaseSlapRecipe
import os
import pkg_resources
import zc.buildout
import zc.recipe.egg
import sys

class Recipe(BaseSlapRecipe):
  def __init__(self, buildout, name, options):
    self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)
    BaseSlapRecipe.__init__(self, buildout, name, options)

  def _install(self):
    self.requirements, self.ws = self.egg.working_set()
    path_list = []
    CONFIG = dict()
    CONFIG['slapos_directory'] = self.createDataDirectory('slapos')
    CONFIG['working_directory'] = self.createDataDirectory('testnode')
    CONFIG['test_suite_directory'] = self.createDataDirectory('test_suite')
    CONFIG['proxy_host'] = self.getLocalIPv4Address()
    CONFIG['proxy_port'] = '5000'
    CONFIG['log_directory'] = self.createDataDirectory('testnodelog')
    CONFIG['run_directory'] = self.createDataDirectory('testnoderun')
    CONFIG['test_suite_title'] = self.parameter_dict.get('test_suite_title')
    CONFIG['test_node_title'] = self.parameter_dict.get('test_node_title')
    CONFIG['test_suite'] = self.parameter_dict.get('test_suite')
    CONFIG['node_quantity'] = self.parameter_dict.get('node_quantity', '1')
    CONFIG['project_title'] = self.parameter_dict.get('project_title')
    CONFIG['ipv4_address'] = self.getLocalIPv4Address()
    CONFIG['ipv6_address'] = self.getGlobalIPv6Address()
    CONFIG['test_suite_master_url'] = self.parameter_dict.get(
                                'test_suite_master_url', None)
    CONFIG['git_binary'] = self.options['git_binary']
    CONFIG['slapgrid_partition_binary'] = self.options[
      'slapgrid_partition_binary']
    CONFIG['slapgrid_software_binary'] = self.options[
      'slapgrid_software_binary']
    CONFIG['slapproxy_binary'] = self.options['slapproxy_binary']
    CONFIG['zip_binary'] = self.options['zip_binary']
    CONFIG['PATH'] = os.environ['PATH']

    CONFIG['instance_dict'] = ''
    if 'instance_dict' in self.parameter_dict:
      CONFIG['instance_dict'] = '[instance_dict]\n'
      for k,v in eval(self.parameter_dict['instance_dict']).iteritems():
        CONFIG['instance_dict'] += '%s = %s\n' % (k,v)

    CONFIG['repository_list'] = ''
    i = 0
    for repository in eval(self.parameter_dict['vcs_repository_list']):
      CONFIG['repository_list'] += '[vcs_repository_%s]\n' % i
      CONFIG['repository_list'] += 'url = %s\n' % repository['url']
      if 'branch' in repository:
        CONFIG['repository_list'] += 'branch = %s\n' % repository['branch']
      if 'profile_path' in repository:
        CONFIG['repository_list'] += 'profile_path = %s\n' % repository[
          'profile_path']
      if 'buildout_section_id' in repository:
        CONFIG['repository_list'] += 'buildout_section_id = %s\n' % repository[
          'buildout_section_id']
      CONFIG['repository_list'] += '\n'
      i += 1
    testnode_config = self.createConfigurationFile('erp5testnode.cfg',
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          'template/erp5testnode.cfg.in'), CONFIG))
    testnode_log = os.path.join(self.log_directory, 'erp5testnode.log')
    wrapper = zc.buildout.easy_install.scripts([('erp5testnode',
     'slapos.recipe.librecipe.execute', 'executee')], self.ws, sys.executable,
      self.wrapper_directory, arguments=[self.options['testnode'], '-l',
      testnode_log, testnode_config], {'GIT_SSL_NO_VERIFY': '1'})[0]
    path_list.append(testnode_config)
    path_list.append(wrapper)
    return path_list
