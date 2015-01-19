##############################################################################
#
# Copyright (c) 2014 Vifib SARL and Contributors. All Rights Reserved.
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
import unittest
import shutil
import tempfile
import slapos.slap
import slapos.cli.configure_local
from slapos.cli.configure_local import ConfigureLocalCommand, _createConfigurationDirectory 
from slapos.cli.entry import SlapOSApp
from argparse import Namespace
from ConfigParser import ConfigParser

# Disable any command to launch slapformat and supervisor
slapos.cli.configure_local._runFormat = lambda x: "Do nothing"
slapos.cli.configure_local.launchSupervisord = lambda instance_root, logger: "Do nothing"

class TestConfigureLocal(unittest.TestCase):

    def setUp(self):
        self.slap = slapos.slap.slap()
        self.app = SlapOSApp()
        self.temp_dir = tempfile.mkdtemp()
        os.environ["HOME"] = self.temp_dir
        self.instance_root = tempfile.mkdtemp()
        self.software_root = tempfile.mkdtemp()
        if os.path.exists(self.temp_dir):
          shutil.rmtree(self.temp_dir)

    def tearDown(self):
        for temp_path in (self.temp_dir, \
          self.instance_root, self.software_root):
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)

    def test_configure_local_environment_with_default_value(self):
        config = ConfigureLocalCommand(self.app, Namespace())
        config.__dict__.update({i.dest: i.default \
          for i in config.get_parser(None)._option_string_actions.values()})
        config.slapos_configuration_directory = self.temp_dir
        config.slapos_buildout_directory = self.temp_dir
        config.slapos_instance_root = self.instance_root
        slapos.cli.configure_local.do_configure(
            config, config.fetch_config, self.app.log)
        expected_software_root = "/opt/slapgrid"
        self.assertTrue(
            os.path.exists("%s/.slapos/slapos-client.cfg" % self.temp_dir))
        with open(self.temp_dir + '/slapos-proxy.cfg') as fout:
            proxy_config = ConfigParser()
            proxy_config.readfp(fout)
            self.assertEquals(proxy_config.get('slapos', 'instance_root'),
                self.instance_root)
            self.assertEquals(proxy_config.get('slapos', 'software_root'),
                expected_software_root)
        with open(self.temp_dir + '/slapos.cfg') as fout:
            proxy_config = ConfigParser()
            proxy_config.readfp(fout)
            self.assertEquals(proxy_config.get('slapos', 'instance_root'),
                self.instance_root)
            self.assertEquals(proxy_config.get('slapos', 'software_root'),
                expected_software_root)

    def test_configure_local_environment(self):
        config = ConfigureLocalCommand(self.app, Namespace())
        config.__dict__.update({i.dest: i.default \
          for i in config.get_parser(None)._option_string_actions.values()})
        config.slapos_configuration_directory = self.temp_dir
        config.slapos_buildout_directory = self.temp_dir
        config.slapos_instance_root = self.instance_root
        config.slapos_software_root = self.software_root
        slapos.cli.configure_local.do_configure(
            config, config.fetch_config, self.app.log)
        log_folder = os.path.join(config.slapos_buildout_directory, 'log')
        self.assertTrue(os.path.exists(log_folder), "%s not exists" % log_folder)
        self.assertTrue(
            os.path.exists("%s/.slapos/slapos-client.cfg" % self.temp_dir))
        with open(self.temp_dir + '/slapos-proxy.cfg') as fout:
            proxy_config = ConfigParser()
            proxy_config.readfp(fout)
            self.assertEquals(proxy_config.get('slapos', 'instance_root'),
                self.instance_root)
            self.assertEquals(proxy_config.get('slapos', 'software_root'),
                self.software_root)
        with open(self.temp_dir + '/slapos.cfg') as fout:
            proxy_config = ConfigParser()
            proxy_config.readfp(fout)
            self.assertEquals(proxy_config.get('slapos', 'instance_root'),
                self.instance_root)
            self.assertEquals(proxy_config.get('slapos', 'software_root'),
                self.software_root)
            log_file = proxy_config.get('slapformat', 'log_file')
            self.assertTrue(log_file.startswith(log_folder),
                "%s don't starts with %s" % (log_file, log_folder))
