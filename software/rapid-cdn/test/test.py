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

import json
import os
import shutil
import subprocess
import tempfile
import slapos.slap.standalone

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class CaucaseBinaryClient(object):
  # Class to mimic user, which is using caucase binaries and some directories
  # to be a client, thus real binaries are used with executable call examples
  def __init__(self, path, url):
    self.path = path
    os.mkdir(self.path)
    self.url = url

    def makepath(p):
      return os.path.join(self.path, p)
    self.client_csr = makepath('client.csr.pem')
    self.client = makepath('client.pem')
    self.ca_crt = makepath('ca-crt.pem')
    self.user_ca_crt = makepath('user-ca-crt.pem')
    self.crl = makepath('crl.pem')
    self.user_crl = makepath('user-crl.pem')
    subprocess.check_call([
      "openssl", "req", "-out", self.client_csr, "-new", "-newkey", "rsa:2048",
      "-nodes", "-keyout", self.client, "-subj", "/CN=user"])
    self.cau_list = [
      "caucase", "--ca-url", self.url, "--ca-crt", self.ca_crt,
      "--user-ca-crt", self.user_ca_crt, "--crl", self.crl, "--user-crl",
      self.user_crl]
    self.user_cau_list = self.cau_list + ["--mode", "user"]
    self.service_cau_list = self.cau_list + [
      "--user-key", self.client, "--mode", "service"]
    output = subprocess.check_output(
      self.user_cau_list + ["--send-csr", self.client_csr])
    subprocess.check_call(
      self.user_cau_list + ["--get-crt", output.split()[0], self.client])

  def signServiceCsr(self, ou):
    for line in subprocess.check_output(
      self.service_cau_list + ["--list-csr"]).splitlines():
      splitted = line.decode().split('|')
      if len(splitted) == 2:
        if 'OU=%s)' % (ou,) in splitted[1]:
          csr_id = splitted[0].strip()
          subprocess.check_call(self.service_cau_list + ["--sign-csr", csr_id])
          break


class Test(SlapOSInstanceTestCase):
  # full diffs are very informative for those tests
  maxDiff = None
  ## as instantiation is split in chunks with cluster administrator operations,
  ## let it run a bit rarely
  #instance_max_retry = 5

  @classmethod
  def _setUpClass(cls):
    cls.work_dir = tempfile.mkdtemp()
    try:
      super()._setUpClass()
    except slapos.slap.standalone.SlapOSNodeInstanceError:
      pass

    # Cluster is initially setup, now it's required to allow joining nodes,
    # which is usually cluster administrator responsibility
    connection_parameter_dict = json.loads(
      cls.requestDefaultInstance().getConnectionParameterDict()['_'])

    cls.kedifa_caucase_client = CaucaseBinaryClient(
      os.path.join(cls.work_dir, 'kedifa_caucase'),
      connection_parameter_dict['kedifa-caucase-url'])
    cls.kedifa_caucase_client.signServiceCsr("Kedifa Partition")

    # Time travel to the future: restart all caucase updaters, so they will
    # pick up just signed service CSR; note that in reality the cluster
    # administrator can wait for the caucase updater to kick in
    with cls.slap.instance_supervisor_rpc as instance_supervisor_rpc:
      for process in instance_supervisor_rpc.getAllProcessInfo():
        if 'caucase-updater' in process['name']:
          process_id = '%(group)s:%(name)s' % process
          instance_supervisor_rpc.stopProcess(process_id)
          instance_supervisor_rpc.startProcess(process_id)

    cls.waitForInstance()

  @classmethod
  def tearDownClass(cls):
    super().tearDownClass()
    shutil.rmtree(cls.work_dir)

  def test_connection_parameter(self):
    connection_parameter_dict = self.requestDefaultInstance(
      ).getConnectionParameterDict()
    self.assertIn('_', connection_parameter_dict)
    json_parmeter_dict = json.loads(connection_parameter_dict.pop('_'))
    self.assertEqual({}, connection_parameter_dict)
    self.assertNotIn('__NotReadyYet__' in json_parmeter_dict.pop('key-generate-auth-url'))
    self.assertNotIn('__NotReadyYet__' in json_parmeter_dict.pop('key-upload-url'))
    self.assertEqual(
      {
        'kedifa-caucase-url': 'http://[::2]:8090',
        'monitor-base-url': 'https://[::2]:8196',
        'monitor-setup-url':
        'https://monitor.app.officejs.com/#page=settings_configurator&url=https://[::2]:8196/public/feeds&username=admin&password=ykozqtld',
        'xxx-replace-with-information-fetch-depends':
        'slapos.cookbook:requestoptional.serialised\nslapos.cookbook:requestoptional.serialised'
      },
      json_parmeter_dict)
