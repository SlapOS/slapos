##############################################################################
#
# Copyright (c) 2013 Vifib SARL and Contributors. All Rights Reserved.
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

import logging
import pprint
import unittest
import tempfile
import StringIO
import sys

from mock import patch, create_autospec

import slapos.cli.console
import slapos.cli.entry
import slapos.cli.info
import slapos.cli.list
import slapos.cli.supervisorctl
from slapos.client import ClientConfig
import slapos.grid.svcbackend
import slapos.proxy
import slapos.slap

import supervisor.supervisorctl

def raiseNotFoundError(*args, **kwargs):
  raise slapos.slap.NotFoundError()

class CliMixin(unittest.TestCase):
  def setUp(self):
    slap = slapos.slap.slap()
    self.local = {'slap': slap}
    self.logger = create_autospec(logging.Logger)
    self.conf = create_autospec(ClientConfig)

class TestCliProxy(CliMixin):
  def test_generateSoftwareProductListFromString(self):
    """
    Test that generateSoftwareProductListFromString correctly parses a parameter
    coming from the configuration file.
    """
    software_product_list_string = """
product1 url1
product2 url2"""
    software_release_url_list = {
        'product1': 'url1',
        'product2': 'url2',
    }
    self.assertEqual(
        slapos.proxy._generateSoftwareProductListFromString(
            software_product_list_string),
        software_release_url_list
    )

  def test_generateSoftwareProductListFromString_emptyString(self):
    self.assertEqual(
        slapos.proxy._generateSoftwareProductListFromString(''),
        {}
    )

class TestCliList(CliMixin):
  def test_list(self):
    """
    Test "slapos list" command output.
    """
    return_value = {
      'instance1': slapos.slap.SoftwareInstance(_title='instance1', _software_release_url='SR1'),
      'instance2': slapos.slap.SoftwareInstance(_title='instance2', _software_release_url='SR2'),
    }
    with patch.object(slapos.slap.slap, 'getOpenOrderDict', return_value=return_value) as _:
      slapos.cli.list.do_list(self.logger, None, self.local)

    self.logger.info.assert_any_call('%s %s', 'instance1', 'SR1')
    self.logger.info.assert_any_call('%s %s', 'instance2', 'SR2')

  def test_emptyList(self):
    with patch.object(slapos.slap.slap, 'getOpenOrderDict', return_value={}) as _:
      slapos.cli.list.do_list(self.logger, None, self.local)

    self.logger.info.assert_called_once_with('No existing service.')

@patch.object(slapos.slap.slap, 'registerOpenOrder', return_value=slapos.slap.OpenOrder())
class TestCliInfo(CliMixin):
  def test_info(self, _):
    """
    Test "slapos info" command output.
    """
    setattr(self.conf, 'reference', 'instance1')
    instance = slapos.slap.SoftwareInstance(
        _software_release_url='SR1',
        _requested_state = 'mystate',
        _connection_dict = {'myconnectionparameter': 'value1'},
        _parameter_dict = {'myinstanceparameter': 'value2'}
    )
    with patch.object(slapos.slap.OpenOrder, 'getInformation', return_value=instance):
      slapos.cli.info.do_info(self.logger, self.conf, self.local)

    self.logger.info.assert_any_call(pprint.pformat(instance._parameter_dict))
    self.logger.info.assert_any_call('Software Release URL: %s', instance._software_release_url)
    self.logger.info.assert_any_call('Instance state: %s', instance._requested_state)
    self.logger.info.assert_any_call(pprint.pformat(instance._parameter_dict))
    self.logger.info.assert_any_call(pprint.pformat(instance._connection_dict))

  def test_unknownReference(self, _):
    """
    Test "slapos info" command output in case reference
    of service is not known.
    """
    setattr(self.conf, 'reference', 'instance1')
    with patch.object(slapos.slap.OpenOrder, 'getInformation', side_effect=raiseNotFoundError):
      slapos.cli.info.do_info(self.logger, self.conf, self.local)

    self.logger.warning.assert_called_once_with('Instance %s does not exist.', self.conf.reference)


@patch.object(supervisor.supervisorctl, 'main')
class TestCliSupervisorctl(CliMixin):
  def test_allow_supervisord_launch(self, _):
    """
    Test that "slapos node supervisorctl" tries to launch supervisord
    """
    instance_root = '/foo/bar'
    with patch.object(slapos.grid.svcbackend, 'launchSupervisord') as launchSupervisord:
      slapos.cli.supervisorctl.do_supervisorctl(self.logger, instance_root, ['status'], False)
      launchSupervisord.assert_any_call(instance_root=instance_root, logger=self.logger)

  def test_forbid_supervisord_launch(self, _):
    """
    Test that "slapos node supervisorctl" does not try to launch supervisord
    """
    instance_root = '/foo/bar'
    with patch.object(slapos.grid.svcbackend, 'launchSupervisord') as launchSupervisord:
      slapos.cli.supervisorctl.do_supervisorctl(self.logger, instance_root, ['status'], True)
      self.assertFalse(launchSupervisord.called)


class TestCliConsole(unittest.TestCase):
  def setUp(self):
    cp = slapos.slap.ComputerPartition('computer_id', 'partition_id')
    cp._parameter_dict = {'parameter_name': 'parameter_value'}

    request_patch = patch.object(slapos.slap.OpenOrder, 'request', return_value = cp)
    self.mock_request = request_patch.start()

    self.config_file = tempfile.NamedTemporaryFile()
    self.config_file.write('''[slapos]
master_url=null
''')
    self.config_file.flush()

  def tearDown(self):
    self.mock_request.stop()
    self.config_file.close()

  def test_console_interactive(self):
      app = slapos.cli.entry.SlapOSApp()
      saved_stdin = sys.stdin
      saved_stdout = sys.stdout
      try:
        sys.stdin = app_stdin = StringIO.StringIO(
            """print request('software_release', 'instance').getInstanceParameterDict()['parameter_name']\n""")
        sys.stdout = app_stdout = StringIO.StringIO()
        app.run(('console', '--cfg', self.config_file.name))
      finally:
        sys.sdin = saved_stdin
        sys.stdout = saved_stdout

      self.mock_request.assert_called_once_with('software_release', 'instance')
      self.assertIn('parameter_value', app_stdout.getvalue())

  def test_console_script(self):
    with tempfile.NamedTemporaryFile() as script:
      script.write(
        """print request('software_release', 'instance').getInstanceParameterDict()['parameter_name']\n""")
      script.flush()

      app = slapos.cli.entry.SlapOSApp()
      saved_stdout = sys.stdout
      try:
        sys.stdout = app_stdout = StringIO.StringIO()
        app.run(('console', '--cfg', self.config_file.name, script.name))
      finally:
        sys.stdout = saved_stdout

      self.mock_request.assert_called_once_with('software_release', 'instance')
      self.assertIn('parameter_value', app_stdout.getvalue())

