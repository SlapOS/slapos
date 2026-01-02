##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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
from __future__ import unicode_literals

import json
import os
import pathlib
import subprocess
import re
import requests
from urllib.parse import urljoin

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../software.cfg')))
repo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../test/hello-vue'))

if not os.path.isdir(os.path.join(repo_path, '.git')):
    subprocess.check_call(['git', 'init'], cwd=repo_path)
    subprocess.check_call(['git', 'config', 'user.name', 'SlapOS Test'], cwd=repo_path)
    subprocess.check_call(['git', 'config', 'user.email', 'slapos-test@example.invalid'], cwd=repo_path)
    subprocess.check_call(['git', 'add', '.'], cwd=repo_path)
    subprocess.check_call(['git', 'commit', '-m', 'initial commit'], cwd=repo_path)

default_npm_project_url = pathlib.Path(repo_path).resolve().as_uri()

class TestNpmeProject(SlapOSInstanceTestCase):
  __partition_reference__ = 'G'

  @classmethod
  def getInstanceParameterDict(cls):
    return {
      'repo-url': default_npm_project_url,
      'branch': "master",
    }

  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def test_url_get(self):
    resp = requests.get(self.connection_parameters['backend-url'], verify=False)
    self.assertEqual(requests.codes.ok, resp.status_code)
    html = resp.text

    # 1. not the original source code index.html
    self.assertNotIn('/src/main.js', html)

    # 2. it should contains the js file built by Vite
    script_match = re.search(
        r'<script[^>]+type="module"[^>]+src="([^"]*assets/[^"]+\.js)"',
        html,
    )
    self.assertIsNotNone(script_match, html)

    js_url = urljoin(self.connection_parameters['backend-url'], script_match.group(1))
    js_resp = requests.get(js_url, verify=False)
    self.assertEqual(requests.codes.ok, js_resp.status_code)

    # 3. createApp is the entry point of Vue 3, the JS file should contains it.
    self.assertIn('createApp', js_resp.text)
    self.assertIn('HelloWorld', js_resp.text)