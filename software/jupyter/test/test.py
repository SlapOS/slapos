##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
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


import http.client
import json
import os
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestJupyter(InstanceTestCase):

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertTrue('_' in parameter_dict)
    try:
      connection_dict = json.loads(parameter_dict['_'])
    except Exception as e:
      self.fail("Can't parse json in %s, error %s" % (parameter_dict['_'], e))

    self.assertTrue('password' in connection_dict)
    password = connection_dict['password']

    self.assertEqual(
      {
        'jupyter-classic-url': 'https://[%s]:8888/tree' % (self._ipv6_address, ),
        'jupyterlab-url': 'https://[%s]:8888/lab' % (self._ipv6_address, ),
        'password': '%s' % (password, ),
        'url': 'https://[%s]:8888/tree' % (self._ipv6_address, )
      },
      connection_dict
    )

    result = requests.get(
      connection_dict['url'], verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['jupyter-classic-url'],
      verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['jupyterlab-url'],
      verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Flab'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )


class TestJupyterPassword(InstanceTestCase):
  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertTrue('_' in parameter_dict)
    try:
      connection_dict = json.loads(parameter_dict['_'])
    except Exception as e:
      self.fail("Can't parse json in %s, error %s" % (parameter_dict['_'], e))

    url = connection_dict['url']
    with requests.Session() as s:
      resp = s.get(url, verify=False)
      result = s.post(
        resp.url,
        verify = False,
        data={"_xsrf": s.cookies["_xsrf"], "password": connection_dict['password']}
      )
      self.assertEqual(
        [http.client.OK, url],
        [result.status_code, result.url]
      )


class TestJupyterAdditional(InstanceTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'frontend-additional-instance-guid': 'SOMETHING'
    }

  def test(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    self.assertTrue('_' in parameter_dict)
    try:
      connection_dict = json.loads(parameter_dict['_'])
    except Exception as e:
      self.fail("Can't parse json in %s, error %s" % (parameter_dict['_'], e))

    result = requests.get(
      connection_dict['url'], verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['jupyter-classic-url'],
      verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['jupyterlab-url'],
      verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Flab'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['url-additional'], verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['jupyter-classic-url-additional'],
      verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Ftree'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )

    result = requests.get(
      connection_dict['jupyterlab-url-additional'],
      verify=False, allow_redirects=False)
    self.assertEqual(
      [http.client.FOUND, True, '/login?next=%2Flab'],
      [result.status_code, result.is_redirect, result.headers['Location']]
    )
