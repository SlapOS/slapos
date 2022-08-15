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
import sqlite3

from slapos.proxy.db_version import DB_VERSION
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, InstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestJupyter(InstanceTestCase):

  def test(self):
    connection_dict = self.computer_partition.getConnectionParameterDict()

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


class TestJupyterAdditional(InstanceTestCase):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'frontend-additional-instance-guid': 'SOMETHING'
    }

  def test(self):
    connection_dict = self.computer_partition.getConnectionParameterDict()

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


class TestJupyterPassword(InstanceTestCase):
  def test(self):
    connection_dict = self.computer_partition.getConnectionParameterDict()

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


class SelectMixin(object):
  def sqlite3_connect(self):
    sqlitedb_file = os.path.join(
      os.path.abspath(
        os.path.join(
          self.slap.instance_directory, os.pardir
        )
      ), 'var', 'proxy.db'
    )
    return sqlite3.connect(sqlitedb_file)

  def select(self, table, fields=('*',), **where):
    db = self.sqlite3_connect()
    try:
      db.row_factory = lambda cursor, row: {
        col[0]: row[idx]
        for idx, col in enumerate(cursor.description)
      }
      return db.execute("SELECT %s FROM %s%s%s" % (
        ", ".join(fields),
        table, DB_VERSION,
        " WHERE " + " AND ".join("%s='%s'" % x for x in where.items())
        if where else "",
      )).fetchall()
    finally:
      db.close()


class TestJupyterCustomFrontend(SelectMixin, InstanceTestCase):
  instance_parameter_dict = {}
  frontend_software_url = 'hello://frontend.url'
  frontend_software_type = 'hello-type'
  frontend_instance_name = 'Hello Frontend'

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  def test(self):

    # create a fake master instance for the frontend slave request
    r = self.slap.request(
        software_release=self.frontend_software_url,
        software_type=self.frontend_software_type,
        partition_reference= "Fake master instance",
    )

    # update the request parameters of the test instance
    self.instance_parameter_dict.update({
      'frontend-software-url': self.frontend_software_url,
      'frontend-software-type': self.frontend_software_type,
      'frontend-instance-name': self.frontend_instance_name,
      'frontend-instance-guid': r._partition_id,
    })
    self.requestDefaultInstance()

    # wait for the instance to converge to the new state
    try:
      self.slap.waitForInstance()
    except Exception:
      pass

    selection = self.select("slave", hosted_by=r._partition_id)

    self.assertEqual(len(selection), 1)

    # clean up the fake master
    r.destroyed()


class TestJupyterCustomAdditional(SelectMixin, InstanceTestCase):
  instance_parameter_dict = {}
  frontend_additional_software_url = 'hello://frontend.url'
  frontend_additional_software_type = 'hello-type'
  frontend_additional_instance_name = 'Hello Frontend'

  @classmethod
  def getInstanceParameterDict(cls):
    return cls.instance_parameter_dict

  def test(self):

    # create a fake master instance for the frontend slave request
    r = self.slap.request(
        software_release=self.frontend_additional_software_url,
        software_type=self.frontend_additional_software_type,
        partition_reference= "Fake master instance",
    )

    # update the request parameters of the test instance
    self.instance_parameter_dict.update({
      'frontend-additional-software-url': self.frontend_additional_software_url,
      'frontend-additional-software-type': self.frontend_additional_software_type,
      'frontend-additional-instance-name': self.frontend_additional_instance_name,
      'frontend-additional-instance-guid': r._partition_id,
    })
    self.requestDefaultInstance()

    # wait for the instance to converge to the new state
    try:
      self.slap.waitForInstance()
    except Exception:
      pass

    selection = self.select("slave", hosted_by=r._partition_id)

    self.assertEqual(len(selection), 1)

    # clean up the fake master
    r.destroyed()
