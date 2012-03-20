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
import sys
import zc.buildout
import zc.recipe.egg


class Recipe(BaseSlapRecipe):
  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    ipv4 = self.getLocalIPv4Address()
    ipv6 = self.getGlobalIPv6Address()
    proxy_port = '50000'
    runner_port = '50000'
    workdir = self.createDataDirectory('runner')
    software_root = os.path.join(workdir, 'software')
    instance_root = os.path.join(workdir, 'instance')
    configuration = dict(
        software_root=software_root,
        instance_root=instance_root,
        master_url='http://%s:%s/' % (ipv4, proxy_port),
        computer_id='slaprunner',
        partition_amount=2,
        slapgrid_sr=self.options['slapgrid_sr'],
        slapgrid_cp=self.options['slapgrid_cp'],
        slapproxy=self.options['slapproxy'],
        supervisor=self.options['supervisor'],
        supervisord_config=os.path.join(instance_root, 'etc',
          'supervisord.conf'),
        runner_workdir=workdir,
        runner_host=ipv6,
        runner_port=runner_port,
        ipv4_address=ipv4,
        ipv6_address=ipv6,
        proxy_host=ipv4,
        proxy_port=proxy_port,
        proxy_database=os.path.join(workdir, 'proxy.db'),
	git=self.options['git'],
	ssh_client=self.options['ssh_client'],
	public_key=self.options['public_key'],
	private_key=self.options['private_key']
    )
    config_file = self.createConfigurationFile('slapos.cfg',
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          'template/slapos.cfg.in'), configuration))
    self.path_list.append(config_file)
    
    environment = dict(
        PATH=os.path.dirname(self.options['git']) + ':' + os.environ['PATH'],
        GIT_SSH=self.options['ssh_client']
    )
    launch_args = [self.options['slaprunner'].strip(), config_file, '--debug']
    self.path_list.extend(zc.buildout.easy_install.scripts([('slaprunner',
      'slapos.recipe.librecipe.execute', 'executee')], self.ws, sys.executable,
      self.wrapper_directory, arguments=[launch_args, environment]))
    self.setConnectionDict(dict(url='http://[%s]:%s' % (ipv6, runner_port)))
    return self.path_list
