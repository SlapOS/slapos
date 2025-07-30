##############################################################################
#
# Copyright (c) 2021 Nexedi SA and Contributors. All Rights Reserved.
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
import requests
import time

from slapos.slap import exception
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class WrenAITestCase(SlapOSInstanceTestCase):
    """
    Common class for testing the components of the WrenAI stack.
    It inherits from SlapOSInstanceTestCase which:
      * Install the software release.
      * Checks it compile without issue.
      * Deploy the software instance.
      * Check that the deployment works and that the promise passes.
    """

    def checkUrlAndGetResponse(self, url):
        response = requests.get(url)
        self.assertEqual(requests.codes['OK'], response.status_code)
        return response

    def test_wren_engine_reported_active(self):
        instance = self.requestDefaultInstance()
        param_dict = instance.getConnectionParameterDict()
        assert 'wren-engine-http-url' in param_dict

    def test_ibis_server_reported_active(self):
        instance = self.requestDefaultInstance()
        param_dict = instance.getConnectionParameterDict()
        assert 'ibis-server-http-url' in param_dict

    def test_wren_ai_reported_active(self):
        instance = self.requestDefaultInstance()
        param_dict = instance.getConnectionParameterDict()
        assert 'wren-ai-http-url' in param_dict

    def test_wren_ui_reported_active(self):
        self.slap.waitForInstance(self.instance_max_retry)
        instance = self.requestDefaultInstance()
        param_dict = instance.getConnectionParameterDict()
        assert 'wren-ui-http-url' in param_dict
        time.sleep(1)
        response = self.checkUrlAndGetResponse(param_dict['wren-ui-http-url'])

    def test_qdrant_http_reported_active(self):
        instance = self.requestDefaultInstance()
        param_dict = instance.getConnectionParameterDict()
        assert 'qdrant-http-url' in param_dict

    def test_qdrant_grpc_reported_active(self):
        instance = self.requestDefaultInstance()
        param_dict = instance.getConnectionParameterDict()
        assert 'qdrant-grpc-endpoint' in param_dict
