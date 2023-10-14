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

import contextlib
import glob
import json
import os
import ssl
import sys
import tempfile
import time

import requests
import urllib.parse
import xmlrpc.client
import urllib3

from slapos.grid.utils import md5digest
from slapos.testing.testcase import (
  SlapOSNodeCommandError,
  installSoftwareUrlList,
  makeModuleSetUpAndTestCaseClass,
)

old_software_release_url = 'https://lab.nexedi.com/nexedi/slapos/raw/1.0.167.9/software/erp5/software.cfg'
new_software_release_url = os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..', 'software.cfg'))

_, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  old_software_release_url,
  software_id="upgrade_erp5",
  skip_software_check=True,
)


def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    [old_software_release_url, new_software_release_url],
    debug=SlapOSInstanceTestCase._debug,
  )


class ERP5UpgradeTestCase(SlapOSInstanceTestCase):
  # use short partition names for unix sockets
  __partition_reference__ = 'u'

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
    # request and instantiate with old software url
    super().setUpClass()

    cls.setUpOldInstance()

    # request instance on new software
    cls._current_software_url = new_software_release_url
    cls.logger.debug('requesting instance on new software')
    cls.requestDefaultInstance()

    # wait for slapos node instance
    snapshot_name = "{}.{}.setUpClass new instance".format(
      cls.__module__, cls.__name__)
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
  def tearDownClass(cls):
    cls.session.close()
    super().tearDownClass()

  @classmethod
  def setUpOldInstance(cls):
    cls._default_instance_old_parameter_dict = param_dict = json.loads(
      cls.computer_partition.getConnectionParameterDict()['_'])

    # use a session to retry on failures, when ERP5 is not ready.
    # (see also TestPublishedURLIsReachableMixin)
    cls.session = requests.Session()
    cls.session.mount(
      param_dict['family-default-v6'],
      requests.adapters.HTTPAdapter(
        max_retries=urllib3.util.retry.Retry(
          total=20,
          backoff_factor=.1,
          status_forcelist=(404, 500, 503),
        )))

    # rebuild an url with user and password
    parsed = urllib.parse.urlparse(param_dict['family-default'])
    cls.authenticated_zope_base_url = parsed._replace(
      netloc='{}:{}@{}:{}'.format(
        param_dict['inituser-login'],
        param_dict['inituser-password'],
        parsed.hostname,
        parsed.port,
      ),
      path=param_dict['site-id'] + '/',
    ).geturl()

    cls.zope_base_url = '{family_default_v6}/{site_id}'.format(
      family_default_v6=param_dict['family-default-v6'],
      site_id=param_dict['site-id'],
    )

    # wait for old site creation
    cls.session.get(
      f'{cls.zope_base_url}/person_module',
      auth=requests.auth.HTTPBasicAuth(
        username=param_dict['inituser-login'],
        password=param_dict['inituser-password'],
      ),
      verify=False,
      allow_redirects=False,
    ).raise_for_status()

    # Create scripts to create test data and search catalog for test data.
    @contextlib.contextmanager
    def getXMLRPCClient():
      # don't verify certificate
      ssl_context = ssl.create_default_context()
      ssl_context.check_hostname = False
      ssl_context.verify_mode = ssl.CERT_NONE
      erp5_xmlrpc_client = xmlrpc.client.ServerProxy(
        cls.authenticated_zope_base_url,
        context=ssl_context,
      )
      with erp5_xmlrpc_client:
        yield erp5_xmlrpc_client

    def addPythonScript(script_id, params, body):
      with getXMLRPCClient() as erp5_xmlrpc_client:
        custom = erp5_xmlrpc_client.portal_skins.custom
        try:
          custom.manage_addProduct.PythonScripts.manage_addPythonScript(
            script_id)
        except xmlrpc.client.ProtocolError as e:
          if e.errcode != 302:
            raise
        getattr(custom, script_id).ZPythonScriptHTML_editAction(
          '',
          '',
          params,
          body,
        )

    # a python script to create a person with a name
    addPythonScript(
      script_id='ERP5Site_createTestPerson',
      params='name',
      body='''if 1:
          portal = context.getPortalObject()
          portal.person_module.newContent(
            first_name=name,
          )
          return 'Done.'
        ''',
    )
    # a python script to search for persons by name
    addPythonScript(
      script_id='ERP5Site_searchTestPerson',
      params='name',
      body='''if 1:
          import json
          portal = context.getPortalObject()
          result = [brain.getObject().getTitle() for brain in portal.portal_catalog(
              portal_type='Person',
              title=name,)]
          assert result # raise so that we retry until indexed
          return json.dumps(result)
        ''',
    )

    cls.session.post(
      '{zope_base_url}/ERP5Site_createTestPerson'.format(
        zope_base_url=cls.zope_base_url),
      auth=requests.auth.HTTPBasicAuth(
        username=param_dict['inituser-login'],
        password=param_dict['inituser-password'],
      ),
      data={
        'name': 'before upgrade'
      },
      verify=False,
      allow_redirects=False,
    ).raise_for_status()

    assert cls.session.get(
      '{zope_base_url}/ERP5Site_searchTestPerson'.format(
        zope_base_url=cls.zope_base_url),
      auth=requests.auth.HTTPBasicAuth(
        username=param_dict['inituser-login'],
        password=param_dict['inituser-password'],
      ),
      params={
        'name': 'before upgrade'
      },
      verify=False,
      allow_redirects=False,
    ).json() == ['before upgrade']

  def test_published_url_is_same(self):
    default_instance_new_parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])
    self.assertEqual(
      default_instance_new_parameter_dict['family-default-v6'],
      self._default_instance_old_parameter_dict['family-default-v6'],
    )

  def test_published_url_is_reachable(self):
    default_instance_new_parameter_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])

    # get certificate from caucase
    with tempfile.NamedTemporaryFile(
        prefix="ca.crt.pem",
        mode="w",
        delete=False,
    ) as ca_cert:
      ca_cert.write(
        requests.get(
          urllib.parse.urljoin(
            default_instance_new_parameter_dict['caucase-http-url'],
            '/cas/crt/ca.crt.pem',
          )).text)
      ca_cert.flush()

      self.session.get(
        '{}/{}/login_form'.format(
          default_instance_new_parameter_dict['family-default-v6'],
          default_instance_new_parameter_dict['site-id'],
        ),
        verify=False,
        # TODO: we don't use caucase yet here.
        # verify=ca_cert.name,
      ).raise_for_status()

  def test_all_instances_use_new_software_release(self):
    self.assertEqual(
      {
        os.path.basename(os.readlink(sr))
        for sr in glob.glob(
          os.path.join(
            self.slap.instance_directory,
            '*',
            'software_release',
          ))
      },
      {md5digest(self.getSoftwareURL())},
    )

  def test_catalog_available(self):
    param_dict = json.loads(
      self.computer_partition.getConnectionParameterDict()['_'])

    # data created before upgrade is available
    self.assertEqual(
      self.session.get(
        '{zope_base_url}/ERP5Site_searchTestPerson'.format(
          zope_base_url=self.zope_base_url),
        auth=requests.auth.HTTPBasicAuth(
          username=param_dict['inituser-login'],
          password=param_dict['inituser-password'],
        ),
        params={
          'name': 'before upgrade'
        },
        verify=False,
        allow_redirects=False,
      ).json(), ['before upgrade'])

    # create data after upgrade
    self.session.post(
      '{zope_base_url}/ERP5Site_createTestPerson'.format(
        zope_base_url=self.zope_base_url),
      auth=requests.auth.HTTPBasicAuth(
        username=param_dict['inituser-login'],
        password=param_dict['inituser-password'],
      ),
      data={
        'name': 'after upgrade'
      },
      verify=False,
      allow_redirects=False,
    ).raise_for_status()

    # new data can also be found
    self.assertEqual(
      self.session.get(
        '{zope_base_url}/ERP5Site_searchTestPerson'.format(
          zope_base_url=self.zope_base_url),
        auth=requests.auth.HTTPBasicAuth(
          username=param_dict['inituser-login'],
          password=param_dict['inituser-password'],
        ),
        params={
          'name': 'after upgrade'
        },
        verify=False,
        allow_redirects=False,
      ).json(), ['after upgrade'])
