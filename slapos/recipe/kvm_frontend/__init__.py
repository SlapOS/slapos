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
from slapos.recipe.librecipe import GenericBaseRecipe, GenericSlapRecipe
import json
import traceback
import zc.buildout

class Recipe(GenericSlapRecipe):
  """
  kvm frontend instance configuration.
  """

  def _getRewriteRuleContent(self, slave_instance_list):
    """Generate rewrite rules list from slaves list"""
    rewrite_rule_list = []
    for slave_instance in slave_instance_list:
      self.logger.info("Processing slave instance %s..." %
          slave_instance['slave_reference'])
      # Check for mandatory fields
      if slave_instance.get('host', None) is None:
        self.logger.warn('No "host" parameter is defined for %s slave'\
            'instance. Ignoring it.' % slave_instance['slave_reference'])
        continue
      if slave_instance.get('port', None) is None:
        self.logger.warn('No "host" parameter is defined for %s slave'\
            'instance. Ignoring it.' % slave_instance['slave_reference'])
        continue

      current_slave_dict = dict()

      # Get host, and if IPv6 address, remove "[" and "]"
      current_slave_dict['host'] = slave_instance['host'].\
          replace('[', '').replace(']', '')
      current_slave_dict['port'] = slave_instance['port']

      # Check if target is https or http
      current_slave_dict['https'] = slave_instance.get('https', 'true')
      if current_slave_dict['https'] in GenericBaseRecipe.FALSE_VALUES:
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
    proxy_table = dict()
    for rewrite_rule in rewrite_rule_list:
      proxy_table[rewrite_rule['resource']] = {
          'port': rewrite_rule['port'],
          'host': rewrite_rule['host'],
          'https': rewrite_rule['https'],
      }

    proxy_table_content = json.dumps(proxy_table)
    return proxy_table_content

  def _install(self):
    # Check for mandatory field
    if self.options.get('domain', None) is None:
      raise zc.buildout.UserError('No domain name specified. Please define '
          'the "domain" instance parameter.')
    # Generate rewrite rules
    rewrite_rule_list = self._getRewriteRuleContent(
      json.loads(self.options['slave-instance-list']))
    # Create Map
    map_content = self._getProxyTableContent(rewrite_rule_list)
    map_file = self.createFile(self.options['map-path'], map_content)

    # Create configuration
    conf = open(self.getTemplateFilename('kvm-proxy.js'), 'r')
    conf_file = self.createFile(self.options['conf-path'], conf.read())
    conf.close()

    # Do we create http dummy server used to redirect to https?
    if self.options['http-redirection'] in GenericBaseRecipe.TRUE_VALUES:
      http_redirect_server = '1'
    else:
      http_redirect_server = ''

    config = dict(
      ipv6=self.options['ipv6'],
      ipv4=self.options['ipv4'],
      port=self.options['port'],
      key=self.options['ssl-key-path'],
      certificate=self.options['ssl-cert-path'],
      name=self.options['domain'],
      shell_path=self.options['shell-path'],
      node_path=self.options['node-binary'],
      node_env=self.options['node-env'],
      conf_path=conf_file,
      map_path=map_file,
      plain_http=http_redirect_server,
    )

    runner_path = self.createExecutable(
      self.options['wrapper-path'],
      self.substituteTemplate(self.getTemplateFilename('nodejs_run.in'),
                              config))

    # Send connection parameters of slave instances
    site_url = "https://%s:%s/" % (self.options['domain'], self.options['port'])
    for slave in rewrite_rule_list:
      try:
        self.setConnectionDict(
            dict(url="%s%s" % (site_url, slave['resource']),
                 domainname=self.options['domain'],
                 port=str(self.options['port']),
                 resource=slave['resource']),
            slave['reference'])
      except:
        self.logger.fatal("Error while sending slave %s informations: %s",
           slave['reference'], traceback.format_exc())

    return [map_file, conf_file, runner_path]
