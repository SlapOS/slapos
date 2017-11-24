# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SA and Contributors. All Rights Reserved.
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
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

import random
import transaction
import unittest
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
import functools
from Products.ERP5Type.tests.utils import DummyMailHost
from Products.ERP5Type.Utils import convertToUpperCase
import os
import glob
from functools import wraps
from Products.ERP5Type.tests.utils import createZODBPythonScript
from AccessControl.SecurityManagement import getSecurityManager, \
    setSecurityManager

def changeSkin(skin_name):
  def decorator(func):
    def wrapped(self, *args, **kwargs):
      default_skin = self.portal.portal_skins.default_skin
      self.portal.portal_skins.changeSkin(skin_name)
      self.app.REQUEST.set('portal_skin', skin_name)
      try:
        v = func(self, *args, **kwargs)
      finally:
        self.portal.portal_skins.changeSkin(default_skin)
        self.app.REQUEST.set('portal_skin', default_skin)
      return v
    return wrapped
  return decorator

def simulate(script_id, params_string, code_string):
  def upperWrap(f):
    @wraps(f)
    def decorated(self, *args, **kw):
      if script_id in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_id)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_id, params_string, code_string)
      transaction.commit()
      try:
        result = f(self, *args, **kw)
      finally:
        if script_id in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_id)
        transaction.commit()
      return result
    return decorated
  return upperWrap

def withAbort(func):
  @functools.wraps(func)
  def wrapped(self, *args, **kwargs):
    try:
      func(self, *args, **kwargs)
    finally:
      self.abort()
  return wrapped

class testSlapOSMixin(ERP5TypeTestCase):

  abort_transaction = 0

  def clearCache(self):
    self.portal.portal_caches.clearAllCache()
    self.portal.portal_workflow.refreshWorklistCache()

  #def getDefaultSitePreferenceId(self):
  #  """Default id, usefull method to override
  #  """
  #  return "slapos_default_system_preference"

  def createAlarmStep(self):
    def makeCallAlarm(alarm):
      def callAlarm(*args, **kwargs):
        sm = getSecurityManager()
        self.login()
        try:
          alarm.activeSense(params=kwargs)
          self.commit()
        finally:
          setSecurityManager(sm)
      return callAlarm
    for alarm in self.portal.portal_alarms.contentValues():
      if alarm.isEnabled():
        setattr(self, 'stepCall' + convertToUpperCase(alarm.getId()) \
          + 'Alarm', makeCallAlarm(alarm))

  def createCertificateAuthorityFile(self):
    """Sets up portal_certificate_authority"""
    # reset test CA to have it always count from 0
    open(os.path.join(os.environ['TEST_CA_PATH'], 'serial'), 'w').write('01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'crlnumber'), 'w').write(
        '01')
    open(os.path.join(os.environ['TEST_CA_PATH'], 'index.txt'), 'w').write('')
    private_list = glob.glob('%s/*.key' % os.path.join(os.environ['TEST_CA_PATH'],
                              'private'))
    for private in private_list:
      os.remove(private)
    crl_list = glob.glob('%s/*' % os.path.join(os.environ['TEST_CA_PATH'],
                              'crl'))
    for crl in crl_list:
      os.remove(crl)
    certs_list = glob.glob('%s/*' % os.path.join(os.environ['TEST_CA_PATH'],
                              'certs'))
    for cert in certs_list:
      os.remove(cert)
    newcerts_list = glob.glob('%s/*' % os.path.join(os.environ['TEST_CA_PATH'],
                              'newcerts'))
    for newcert in newcerts_list:
      os.remove(newcert)


  def setupPortalAlarms(self):
    if not self.portal.portal_alarms.isSubscribed():
      self.portal.portal_alarms.subscribe()
    self.assertTrue(self.portal.portal_alarms.isSubscribed())

  def isLiveTest(self):
    #return 'ERP5TypeLiveTestCase' in [q.__name__ for q in self.__class__.mro()]
    # XXX - What is the better way to no if we are in live test mode ?
    return not os.environ.has_key('TEST_CA_PATH')

  def _setUpDummyMailHost(self):
    """Do not play with NON persistent replacement of MailHost"""
    if not self.isLiveTest():
      ERP5TypeTestCase._setUpDummyMailHost(self)

  def _restoreMailHost(self):
    """Do not play with NON persistent replacement of MailHost"""
    if not self.isLiveTest():
      ERP5TypeTestCase._restoreMailHost(self)

  def beforeTearDown(self):
    if self.isLiveTest():
      self.deSetUpPersistentDummyMailHost()
    if self.abort_transaction:
      transaction.abort()

  def getUserFolder(self):
    """
    Return the user folder
    """
    return getattr(self.getPortal(), 'acl_users', None)

  def setUpOnce(self):
    # Reload promise and include yet another bt5 path.
    self.loadPromise(searchable_business_template_list=["erp5_core", "erp5_base", "slapos_configurator"])
    self.portal.portal_alarms.promise_template_tool_configuration.solve()
    self.commit()
    self.launchConfigurator()

  def afterSetUp(self):
    self.login()
    self.createAlarmStep()

    # Helpfull for the tests
    self.new_id = self.generateNewId()

    if self.isLiveTest():
      self.setUpPersistentDummyMailHost()
      return
    self.portal.portal_caches.erp5_site_global_id = '%s' % random.random()
    self.portal.portal_caches._p_changed = 1
    self.commit()
    self.portal.portal_caches.updateCache()
    if getattr(self.portal, 'is_site_bootstrapped', 0):
      for alarm in self.portal.portal_alarms.contentValues():
        if alarm.getId().startswith("promise_slapos"):
           alarm.solve()
      return
    else:
      self.portal.is_site_bootstrapped = 1
      self.bootstrapSite()
      self.portal._p_changed = 1
      self.commit()


  def deSetUpPersistentDummyMailHost(self):
    if 'MailHost' in self.portal.objectIds():
      self.portal.manage_delObjects(['MailHost'])
    self.portal.manage_addProduct['MailHost'].manage_addMailHost('MailHost')
    self.commit()

  def setUpPersistentDummyMailHost(self):
    if 'MailHost' in self.portal.objectIds():
      self.portal.manage_delObjects(['MailHost'])
    self.portal._setObject('MailHost', DummyMailHost('MailHost'))

    self.portal.email_from_address = 'romain@nexedi.com'
    self.portal.email_to_address = 'romain@nexedi.com'

  def getBusinessConfiguration(self):
    return self.portal.business_configuration_module[\
                          "slapos_master_configuration_workflow"]

  def launchConfigurator(self):
    self.login()
    # Create new Configuration 
    business_configuration  = self.getBusinessConfiguration()

    response_dict = {}
    while response_dict.get("command", "next") != "install":
      response_dict = self.portal.portal_configurator._next(
                            business_configuration, {})

    self.tic() 
    self.portal.portal_configurator.startInstallation(
                 business_configuration,REQUEST=self.portal.REQUEST)

  def bootstrapSite(self):
    self.setupPortalAlarms()
    self.createCertificateAuthorityFile()

    self.clearCache()
    self.tic()

  def getBusinessTemplateList(self):
    """
    Install the business templates.
    """
    result = [
      'erp5_full_text_myisam_catalog',
      'erp5_core_proxy_field_legacy',
      'erp5_base',
      'erp5_workflow',
      'erp5_configurator',
      'slapos_configurator',
    ]
    return result


  def makePerson(self, new_id=None, index=True, user=True):

    if new_id is None:
      new_id = self.generateNewId()
    # Clone person document
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()


    if user:
      login = self._addERP5Login(person_user)

    if index:
      transaction.commit()
      person_user.immediateReindexObject()
      if user:
        login.immediateReindexObject()

    return person_user

  def _addERP5Login(self, document):
      login = document.newContent(
        portal_type="ERP5 Login",
        reference=document.getReference())
      login.validate()
      return login

  def _makeTree(self, requested_template_id='template_software_instance'):
    new_id = self.generateNewId()

    self.request_kw = dict(
        software_release=self.generateNewSoftwareReleaseUrl(),
        software_title=self.generateNewSoftwareTitle(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateEmptyXml(),
        shared=False,
        state="started"
    )

    self.person_user = self.makePerson(new_id=new_id, index=False)
    self.commit()
    # prepare part of tree
    self.hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.software_instance = self.portal.software_instance_module\
        [requested_template_id].Base_createCloneDocument(batch_mode=1)

    self.hosting_subscription.edit(
        title=self.request_kw['software_title'],
        reference="TESTHS-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        root_slave=self.request_kw['shared'],
        predecessor=self.software_instance.getRelativeUrl(),
        destination_section=self.person_user.getRelativeUrl()
    )
    self.hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(self.hosting_subscription, 'start_requested')

    self.requested_software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    self.software_instance.edit(
        title=self.request_kw['software_title'],
        reference="TESTSI-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=self.hosting_subscription.getRelativeUrl(),
        predecessor=self.requested_software_instance.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(self.software_instance, 'start_requested')
    self.software_instance.validate()

    self.requested_software_instance.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=self.hosting_subscription.getRelativeUrl(),
    )
    self.portal.portal_workflow._jumpToStateFor(self.requested_software_instance, 'start_requested')
    self.requested_software_instance.validate()
    self.tic()

  def _makeComputer(self, owner=None):
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    reference = 'TESTCOMP-%s' % self.generateNewId()
    self.computer.edit(
        allocation_scope='open/public',
        capacity_scope='open',
        reference=reference,
        title=reference
        )
    self.computer.validate()
    reference = 'TESTPART-%s' % self.generateNewId()
    self.partition = self.computer.newContent(portal_type='Computer Partition',
      reference=reference,
      title=reference
    )
    self.partition.markFree()
    self.partition.validate()
    self.tic()

    if owner is not None:
      self.computer.edit(
        source_administration_value=owner,
      )
    return self.computer, self.partition

  def _makeComputerNetwork(self):
    reference = 'TESTCOMPNETWORK-%s' % self.generateNewId()
    self.computer_network = self.portal.computer_network_module.newContent(
        portal_type='Computer Network',
        reference=reference,
        title=reference
    )
    self.computer_network.validate()
    self.tic()
    return self.computer_network

  def _makeComplexComputer(self, person=None, with_slave=False):
    for i in range(1, 5):
      id_ = 'partition%s' % i
      p = self.computer.newContent(portal_type='Computer Partition',
        id=id_,
        title=id_,
        reference=id_,
        default_network_address_ip_address='ip_address_%s' % i,
        default_network_address_netmask='netmask_%s' % i)
      p.markFree()
      p.validate()

    self.start_requested_software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    self.start_requested_software_installation.edit(
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl(),
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        title='Start requested for %s' % self.computer.getTitle()
    )
    self.start_requested_software_installation.validate()
    self.start_requested_software_installation.requestStart()

    self.destroy_requested_software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    self.destroy_requested_software_installation.edit(
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl(),
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        title='Destroy requested for %s' % self.computer.getTitle()
    )
    self.destroy_requested_software_installation.validate()
    self.destroy_requested_software_installation.requestStart()
    self.destroy_requested_software_installation.requestDestroy()

    self.destroyed_software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    self.destroyed_software_installation.edit(
        url_string=self.generateNewSoftwareReleaseUrl(),
        aggregate=self.computer.getRelativeUrl(),
        reference='TESTSOFTINST-%s' % self.generateNewId(),
        title='Destroyed for %s' % self.computer.getTitle()
    )
    self.destroyed_software_installation.validate()
    self.destroyed_software_installation.requestStart()
    self.destroyed_software_installation.requestDestroy()
    self.destroyed_software_installation.invalidate()

    self.computer.partition1.markBusy()
    self.computer.partition2.markBusy()
    self.computer.partition3.markBusy()

    # prepare some trees
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        destination_section_value=person,
    )
    kw = dict(
      software_release=\
          self.start_requested_software_installation.getUrlString(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)

    self.start_requested_software_instance = hosting_subscription.getPredecessorValue()
    self.start_requested_software_instance.edit(aggregate=self.computer.partition1.getRelativeUrl())

    if with_slave:
      hosting_subscription = self.portal.hosting_subscription_module\
          .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
      hosting_subscription.validate()
      hosting_subscription.edit(
          title=self.generateNewSoftwareTitle(),
          reference="TESTSI-%s" % self.generateNewId(),
          destination_section_value=person,
      )
      slave_kw = dict(
        software_release=kw['software_release'],
        software_type=kw['software_type'],
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        shared=True,
        software_title=hosting_subscription.getTitle(),
        state='started'
      )
      hosting_subscription.requestStart(**slave_kw)
      hosting_subscription.requestInstance(**slave_kw)

      self.start_requested_slave_instance = hosting_subscription.getPredecessorValue()
      self.start_requested_slave_instance.edit(aggregate=self.computer.partition1.getRelativeUrl())

    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
        destination_section_value=person,
    )
    kw = dict(
      software_release=\
          self.start_requested_software_installation.getUrlString(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='stopped'
    )
    hosting_subscription.requestStop(**kw)
    hosting_subscription.requestInstance(**kw)

    self.stop_requested_software_instance = hosting_subscription.getPredecessorValue()
    self.stop_requested_software_instance.edit(
        aggregate=self.computer.partition2.getRelativeUrl()
    )

    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
    )
    kw = dict(
      software_release=\
          self.start_requested_software_installation.getUrlString(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='stopped'
    )
    hosting_subscription.requestStop(**kw)
    hosting_subscription.requestInstance(**kw)

    kw['state'] = 'destroyed'
    hosting_subscription.requestDestroy(**kw)

    self.destroy_requested_software_instance = hosting_subscription.getPredecessorValue()
    self.destroy_requested_software_instance.requestDestroy(**kw)
    self.destroy_requested_software_instance.edit(
        aggregate=self.computer.partition3.getRelativeUrl()
    )

    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTSI-%s" % self.generateNewId(),
    )
    kw = dict(
      software_release=\
          self.start_requested_software_installation.getUrlString(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='stopped'
    )
    hosting_subscription.requestStop(**kw)
    hosting_subscription.requestInstance(**kw)

    kw['state'] = 'destroyed'
    hosting_subscription.requestDestroy(**kw)

    self.destroyed_software_instance = hosting_subscription.getPredecessorValue()
    self.destroyed_software_instance.edit(
        aggregate=self.computer.partition4.getRelativeUrl()
    )
    self.destroyed_software_instance.requestDestroy(**kw)
    self.destroyed_software_instance.invalidate()

    self.tic()
    if with_slave:
      # as slave is created in non usual way update its local roles
      self.start_requested_slave_instance.updateLocalRolesOnSecurityGroups()
      self.tic()
    self._cleaupREQUEST()

  def _makeSoftwareProduct(self, new_id):
    software_product = self.portal.software_product_module\
      .template_software_product.Base_createCloneDocument(batch_mode=1)
    software_product.edit(
      reference='TESTSOFTPROD-%s' % new_id,
      title='Test software product %s' % new_id
    )
    software_product.publish()
    return software_product

  def _makeSoftwareRelease(self, new_id):
    software_release = self.portal.software_release_module\
      .template_software_release.Base_createCloneDocument(batch_mode=1)
    software_release.edit(
      url_string=self.generateNewSoftwareReleaseUrl(),
      reference='TESTSOFTRELS-%s' % new_id,
      title='Start requested for %s' % new_id
    )
    software_release.release()
    return software_release


  def _cleaupREQUEST(self):
    self.portal.REQUEST['request_instance'] = None
    self.portal.REQUEST.headers = {}

  def generateNewId(self):
    return "%sö" % self.portal.portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/têst%s.cfg' % self.generateNewId()

  def generateNewSoftwareType(self):
    return 'Type ë@î %s' % self.generateNewId()

  def generateNewSoftwareTitle(self):
    return 'Title é#ï %s' % self.generateNewId()

  def generateSafeXml(self):
    return '<?xml version="1.0" encoding="utf-8"?><instance><parameter '\
      'id="%s">%s</parameter></instance>' % \
      ("paramé".decode("UTF-8").encode("UTF-8"),
      self.generateNewId().decode("UTF-8").encode("UTF-8"))

  def generateEmptyXml(self):
    return '<?xml version="1.0" encoding="utf-8"?><instance></instance>'

class TestSlapOSDummy(testSlapOSMixin):
  run_all_test = 1
  def test(self):
    """Dummy test in order to fire up Business Template testing"""
    self.assertTrue(True)

  def getTitle(self):
    return "Dummy tests in order to have tests from BT5 run"

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSDummy))
  return suite
