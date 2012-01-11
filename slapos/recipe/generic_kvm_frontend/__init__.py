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
from slapos.recipe.librecipe import GenericBaseRecipe
from json import loads as unjson

class Recipe(GenericBaseRecipe):
  """
  kvm frontend instance configuration.
  """

  def _getRewriteRuleContent(self, slave_instance_list):
    """Generate rewrite rules list from slaves list"""
    rewrite_rule_list = []
    for slave_instance in slave_instance_list:
      current_slave_dict = dict()
      # Get host, and if IPv6 address, remove "[" and "]"
      current_slave_dict['host'] = current_slave_dict['host'].\
          replace('[', '').replace(']', '')
      current_slave_dict['port'] = slave_instance['port']
      if current_slave_dict['host'] is None \
          or current_slave_dict['port'] is None:
        # XXX-Cedric: should raise warning because slave seems badly configured
        continue
      # Check if target is https or http
      current_slave_dict['https'] = slave_instance.get('https', 'true')
      if current_slave_dict['https'] in FALSE_VALUE_LIST:
        current_slave_dict['https'] = 'false'
      # Set reference and resource url
      # Reference is raw reference from SlapOS Master, resource is
      # URL-compatible name
      reference = slave_instance.get('slave_reference')
      current_slave_dict['reference'] = reference
      current_slave_dict['resource'] = reference.replace('-', '')
      rewrite_rule_list.append(current_slave_dict)
    return rewrite_rule_list

  def _getProxyTableContent(self, rewrite_rule_list):
    """Generate proxy table file content from rewrite rules list"""
    proxy_table_content = '{'
    for rewrite_rule in rewrite_rule_list:
      rewrite_part = self.substituteTemplate(
         self.getTemplateFilename('proxytable-resource-snippet.json.in'),
         rewrite_rule)
      proxy_table_content += "%s," % rewrite_part
#     proxy_table_content = '%s%s' % (proxy_table_content,
#          open(self.getTemplateFilename('proxytable-vifib-snippet.json.in')).read())
    proxy_table_content += '}\n'
    return proxy_table_content

  def install(self):
    # Generate rewrite rules
    rewrite_rule_list = self._getRewriteRuleContent(
      unjson(self.options['slave-instance-list']))
    # Create Map
    map_content = self._getProxyTableContent(rewrite_rule_list)
    map_file = self.createFile(self.options['map-path'], map_content)

    # Create configuration
    conf = open(self.getTemplateFilename('kvm-proxy.js'), 'r')
    conf_file = self.createFile(self.options['conf-path'], conf.read())
    conf.close()

    config = dict(
      ip=self.options['ip'],
      port=self.options['port'],
      key=self.options['ssl-key-path'],
      certificate=self.options['ssl-cert-path'],
      name=self.options['domain'],
      shell_path=self.options['shell-path'],
      node_path=self.options['node-binary'],
      node_env=self.options['node-env'],
      conf_path=conf_file,
      map_path=map_file,
      plain_http='',
    )

    runner_path = self.createExecutable(
      self.options['wrapper-path'],
      self.substituteTemplate(self.getTemplateFilename('nodejs_run.in'),
                              config))

    return [map_file, conf_file, runner_path]
