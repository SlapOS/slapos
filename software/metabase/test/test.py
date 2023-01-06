##############################################################################
#
# Copyright (c) 2020 Nexedi SA and Contributors. All Rights Reserved.
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
import json
from urllib import parse
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, MetabaseTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestMetabaseSetup(MetabaseTestCase):
  __partition_reference__ = 'S'  # postgresql use a socket in data dir
  # instance can take time, /api/session/properties timeout at the beginning.
  instance_max_retry = 30

  def test_setup(self):
    url = self.computer_partition.getConnectionParameterDict()['url']
    resp = requests.get(parse.urljoin(url, '/setup'), verify=False)
    self.assertTrue(resp.text)

    # get a setup token as described in https://github.com/metabase/metabase/issues/4240#issuecomment-290717451
    properties = requests.get(
        parse.urljoin(url, '/api/session/properties'), verify=False,
        timeout=10).json()

    email = "youlooknicetoday@email.com"
    password = "password123456"

    request_json = {
        'token': properties['setup-token'],
        'prefs': {
            'allow_tracking': 'false',
            'site_name': 'Org'
        },
        'user': {
            'email': email,
            'password': password,
            'first_name': 'Johnny',
            'last_name': 'Appleseed',
            'site_name': 'Org',
        },
        'database': None
    }
    resp = requests.post(
        parse.urljoin(url, '/api/setup'),
        json=request_json,
        verify=False,
        timeout=5)
    self.assertTrue(resp.ok)

    resp = requests.post(
        parse.urljoin(url, '/api/session'),
        verify=False,
        json={
            "username": email,
            "password": "wrong"
        })
    self.assertEqual(resp.status_code, requests.codes.unauthorized)

    session = requests.post(
        parse.urljoin(url, '/api/session'),
        verify=False,
        json={
            "username": email,
            "password": password
        }).json()
    self.assertTrue(session.get('id'))
