##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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

import json
import os
import time
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'software.cfg')))



class ERP5MariadbCrashTestCase(SlapOSInstanceTestCase):
  __partition_reference__ = 'crash'

  _save_instance_file_pattern_list = SlapOSInstanceTestCase._save_instance_file_pattern_list + (
      '*/srv/mariadb/core',
  )

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        '_':
            json.dumps({
                "bt5": "erp5_full_text_myisam_catalog erp5_configurator_standard erp5_configurator_maxma_demo erp5_configurator_run_my_doc erp5_scalability_test",
                "zope-partition-dict": {
                    "activities": {
                        "instance-count": 6,
                        "family": "activities",
                        "thread-amount": 2,
                        "port-base": 2300
                    },
                    "user": {
                        "instance-count": 1,
                        "family": "user",
                        "port-base": 2200
                    },
                },
            })
    }


  def test_scalability(self):
    connection_parameters = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    erp5_url = '%s/%s' % (connection_parameters['family-user'], connection_parameters['site-id'])

    # wait for ERP5 instanciation to be really finished
    # XXX why isn't this a promise ?
    for i in range(1, 100):
      delay = min(i, 10)
      r = requests.get(erp5_url + '/login_form', verify=False)
      if r.status_code != requests.codes.ok:
        self.logger.warn("retry %d: ERP5 is not available, sleeping for %ds and retrying", i, delay)
        time.sleep(delay)
        continue
      r.raise_for_status()
      break

    erp5_auth = (
        connection_parameters['inituser-login'],
        connection_parameters['inituser-password'],
    )

    def waitForERP5SiteReady(max_retry):
      for i in range(0, max_retry):
        r = requests.get(erp5_url + '/ERP5Site_isReady', auth=erp5_auth, verify=False)
        delay = min(i, 30)
        if r.status_code == requests.codes.not_found:
          self.logger.warn("retry %d: URL was not found, sleeping for %ds and retrying", i, delay)
          time.sleep(delay)
          continue
        r.raise_for_status()
        activity_count = r.json()
        if activity_count != 0:
          self.logger.warn(
              "retry %d: ERP5 is not ready (%d activities pending), sleeping for %ds and retrying",
              i, activity_count, delay)
          time.sleep(delay)
          continue
        self.logger.warn("got reply: %s", r.text)
        break
      else:
        self.fail("ERP5 was not ready after %d retries", max_retry)

    waitForERP5SiteReady(1000)

    requests.get(
        erp5_url + '/ERP5Site_bootstrapScalabilityTest',
        auth=erp5_auth,
        verify=False,
        params={
          'user_quantity:int': 1
        }
    ).raise_for_status()

    # requests.get(erp5_url + '/ERP5Site_bootstrapScalabilityTest', auth=erp5_auth, verify=False, params={'user_quantity:int': 1})
    try:
      waitForERP5SiteReady(10000)
    except Exception:
      import pdb; pdb.post_mortem()
      raise
    import pdb; pdb.set_trace()
