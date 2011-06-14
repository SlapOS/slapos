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
from slapos.lib.recipe.BaseSlapRecipe import BaseSlapRecipe
import os
import pkg_resources
import sys
import zc.buildout
import zc.recipe.egg

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set([__name__])
    # Use killpidfromfile from ERP5.
    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', __name__ + 'slapos.recipe.erp5.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]
    self.path_list.append(self.killpidfromfile)
    conversion_server_conf = self.installConversionServer(
        self.getLocalIPv4Address(), 23000, 23060)

    self.linkBinary()
    self.setConnectionDict(dict(
      site_url="http://%s:%s/" % (self.getLocalIPv4Address(), 23000),
    ))
    return self.path_list

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)

  def installConversionServer(self, ip, port, openoffice_port):
    name = 'conversion_server'
    working_directory = self.createDataDirectory(name)
    conversion_server_dict = dict(
      working_path=working_directory,
      uno_path=self.options['ooo_uno_path'],
      office_binary_path=self.options['ooo_binary_path'],
      ip=ip,
      port=port,
      openoffice_port=openoffice_port,
    )
    for env_line in self.options['environment'].splitlines():
      env_line = env_line.strip()
      if not env_line:
        continue
      if '=' in env_line:
        env_key, env_value = env_line.split('=')
        conversion_server_dict[env_key.strip()] = env_value.strip()
      else:
        raise zc.buildout.UserError('Line %r in environment parameter is '
            'incorrect' % env_line)
    config_file = self.createConfigurationFile(name + '.cfg',
        self.substituteTemplate(self.getTemplateFilename('cloudooo.cfg.in'),
          conversion_server_dict))
    self.path_list.append(config_file)
    # Use execute from erp5.
    self.path_list.extend(zc.buildout.easy_install.scripts([(name,
      __name__ + 'slapos.recipe.librecipe.execute',
      'execute_with_signal_translation')], self.ws,
      sys.executable, self.wrapper_directory,
      arguments=[self.options['ooo_paster'].strip(), 'serve', config_file]))
    return {
      name + '_port': conversion_server_dict['port'],
      name + '_ip': conversion_server_dict['ip']
      }
