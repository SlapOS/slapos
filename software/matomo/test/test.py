##############################################################################
# coding: utf-8
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
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
import io
import os
import urllib.parse
import glob

import lxml.etree
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class MatomoTestCase(SlapOSInstanceTestCase):

  #check where matomo installed
  def setUp(self):
    partition_path_list = glob.glob(os.path.join(self.slap.instance_directory, '*'))
    for partition_path in partition_path_list:
      path = os.path.join(partition_path, 'srv/www')
      if os.path.exists(path):
        self.matomo_path = path
        break
    self.assertTrue(self.matomo_path,"matomo path not found in %r" % (partition_path_list,))
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()
    # parse <url> out of ['<url>']
    url = self.connection_parameters['mariadb-url-list'][2:-2]
    self.db_info = urllib.parse.urlparse(url)

  #Check if matomo root directory is empty
  def test_matomo_dir(self):
    self.assertEqual(os.path.isfile(self.matomo_path),False)

  #Check deployement matomo works
  def test_matomo_url_get(self):
    resp = requests.get(self.connection_parameters['backend-url'], verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)

  #Check deployement moniter works
  def test_monitor_url_get(self):
    resp = requests.get(self.connection_parameters['monitor-setup-url'], verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)

  def test_database_setup(self):
    # Database setup page is prefilled with mariadb connection parameters
    resp = requests.get(
      urllib.parse.urljoin(
        self.connection_parameters['backend-url'],
        'index.php?module=CoreUpdater&action=databaseSetup'),
      verify=False)

    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.parse(io.StringIO(resp.text), parser)
    self.assertEqual(
      tree.xpath('//input[@name="username"]/@value'),
      ['matomo'])
    self.assertEqual(
      tree.xpath('//input[@name="dbname"]/@value'),
      ['matomo'])
    self.assertEqual(
      tree.xpath('//input[@name="password"]/@value'),
      [self.db_info.password])
    self.assertEqual(
      tree.xpath('//input[@name="host"]/@value'),
      [f'{self._ipv4_address}:2099']
    )
