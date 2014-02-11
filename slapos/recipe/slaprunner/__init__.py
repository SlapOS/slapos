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

#XXX-Nicolas This recipe has to be deleted as soon as possible
#No changes allowed, except full-replacement using buildout
class Test(GenericBaseRecipe):
  def _options(self, options):
    self.ipv4 = options['ipv4'].strip()
    self.ipv6 = options['ipv6'].strip()
    self.proxy_port = options['proxy_port'].strip()
    self.runner_port = options['runner_port'].strip()
    self.workdir = options['working-directory'].strip()
    self.software_directory = options['software-directory'].strip()
    self.instance_directory = options['instance-directory'].strip()
    self.partition_amount = options['partition-amount'].strip()
    self.cloud9_url = options.get('cloud9-url', '').strip()
    # Set slaprunner access URL
    options['access-url'] = 'http://[%s]:%s' % (self.ipv6, self.runner_port)

  def install(self):
    path_list = []

    configuration = dict(
        software_root=self.software_directory,
        instance_root=self.instance_directory,
        master_url='http://%s:%s/' % (self.ipv4, self.proxy_port),
        computer_id='slaprunner',
        partition_amount=self.partition_amount,
        slapgrid_sr=self.options['slapgrid_sr'],
        slapgrid_cp=self.options['slapgrid_cp'],
        slapproxy=self.options['slapproxy'],
        supervisor=self.options['supervisor'],
        supervisord_config=os.path.join(self.instance_directory, 'etc',
          'supervisord.conf'),
        runner_workdir=self.workdir,
        etc_dir=self.options['etc_dir'],
        run_dir=self.options['etc_dir'],
        log_dir=self.workdir,
        runner_host=self.ipv4,
        runner_port=self.runner_port,
        ipv4_address=self.ipv4,
        ipv6_address=self.ipv6,
        proxy_host=self.ipv4,
        proxy_port=self.proxy_port,
        proxy_database=os.path.join(self.workdir, 'proxy.db'),
        git=self.options['git-binary'],
        ssh_client=self.options['ssh_client'],
        public_key=self.options['public_key'],
        private_key=self.options['private_key'],
        cloud9_url=self.cloud9_url
    )

    config_file = self.createFile(self.options['slapos.cfg'],
        self.substituteTemplate(self.getTemplateFilename('slapos.cfg.in'),
        configuration))
    path_list.append(config_file)

    environment = dict(
        PATH=os.path.dirname(
            self.options['git-binary']) + ':' + os.environ['PATH'],
        GIT_SSH=self.options['ssh_client'],
        CONFIG_FILE_PATH=config_file
    )
    launch_args = [self.options['slaprunnertest'].strip()]

    wrapper = self.createPythonScript(self.options['wrapper'],
        'slapos.recipe.librecipe.execute.executee',
        (launch_args, environment)
    )
    path_list.append(wrapper)

    return path_list
