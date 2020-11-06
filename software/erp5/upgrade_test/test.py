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

import json
import os
import tempfile
import time
import urlparse

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.testcase import installSoftwareUrlList
from slapos.testing.testcase import SlapOSNodeCommandError


old_software_release_url = 'https://lab.nexedi.com/nexedi/slapos/raw/1.0.167/software/erp5/software.cfg'
new_software_release_url = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))


setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(old_software_release_url)


class ERP5UpgradeTestCase(SlapOSInstanceTestCase):
  @classmethod
  def setUpOldInstance(cls):
    """setUp hook executed while to old instance is running, before update
    """
    pass

  _current_software_url = old_software_release_url
  @classmethod
  def getSoftwareURL(cls):
    return cls._current_software_url

  @classmethod
  def setUpClass(cls):
    # request and instanciate with old software url
    super(ERP5UpgradeTestCase, cls).setUpClass()

    cls.setUpOldInstance()

    cls.logger.debug('supplying new software')
    installSoftwareUrlList(cls, [new_software_release_url], debug=cls._debug)

    # request instance on new software
    cls._current_software_url = new_software_release_url
    cls.logger.debug('requesting instance on new software')
    cls.requestDefaultInstance()

    # wait for slapos node instance
    snapshot_name = "{}.{}.setUpClass new instance".format(cls.__module__, cls.__name__)
    try:
      if cls._debug and cls.instance_max_retry:
        try:
          cls.slap.waitForInstance(max_retry=cls.instance_max_retry - 1)
        except SlapOSNodeCommandError:
          cls.slap.waitForInstance(debug=True)
      else:
        cls.slap.waitForInstance(
            max_retry=cls.instance_max_retry, debug=cls._debug)
      cls.logger.debug("instance on new software done")
    except BaseException:
      cls.logger.exception("Error during instance on new software")
      cls._storeSystemSnapshot(snapshot_name)
      cls._cleanup(snapshot_name)
      cls.setUp = lambda self: self.fail('Setup Class failed.')
      raise
    else:
      cls._storeSystemSnapshot(snapshot_name)

    cls.computer_partition = cls.requestDefaultInstance()


class TestERP5Upgrade(ERP5UpgradeTestCase):
  @classmethod
  def setUpOldInstance(cls):
    cls._default_instance_old_parameter_dict = json.loads(cls.computer_partition.getConnectionParameterDict()['_'])

  def test_published_url_is_same(self):
    default_instance_new_parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
    self.assertEqual(
        default_instance_new_parameter_dict['family-default-v6'],
        self._default_instance_old_parameter_dict['family-default-v6'],
    )

  def test_published_url_is_reachable(self):
    default_instance_new_parameter_dict = json.loads(self.computer_partition.getConnectionParameterDict()['_'])

    # get certificate from caucase
    with tempfile.NamedTemporaryFile(
          prefix="ca.crt.pem",
          mode="w",
          delete=False,
        ) as ca_cert:
      ca_cert.write(
        requests.get(
            urlparse.urljoin(
                default_instance_new_parameter_dict['caucase-http-url'],
                '/cas/crt/ca.crt.pem',
            )).text)
      ca_cert.flush()

      def check_default_url_is_reachable():
        requests.get(
            '{}/{}/login_form'.format(
                default_instance_new_parameter_dict['family-default-v6'],
                default_instance_new_parameter_dict['site-id'],
            ),
            verify=False,
            # TODO: we don't use caucase here.
            # verify=ca_cert.name,
        ).raise_for_status()

      for retry in range(20):
        try:
          check_default_url_is_reachable()
        except Exception:
          self.logger.debug('Error reaching ERP5, sleeping %ss and retrying', retry, exc_info=True)
          time.sleep(retry)
        else:
          break
      check_default_url_is_reachable()
