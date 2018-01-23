##############################################################################
#
# Copyright (c) 2002-2018 Nexedi SA and Contributors. All Rights Reserved.
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
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

from DateTime import DateTime
from Products.ERP5Type.tests.utils import createZODBPythonScript
import transaction
import functools
from functools import wraps


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

class SlapOSTestCaseMixin(testSlapOSMixin):

  def afterSetUp(self):
    testSlapOSMixin.afterSetUp(self)
    self.new_id = self.generateNewId()

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

  def _cleaupREQUEST(self):
    self.portal.REQUEST['request_instance'] = None
    self.portal.REQUEST.headers = {}

  def generateNewId(self):
    return "%sö" % self.portal.portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Transaction %s" % new_id,
      reference="TESTTRANS-%s" % new_id,
      )

  def createSaleInvoiceTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      title="Invoice %s" % new_id,
      reference="TESTSIT-%s" % new_id,
      )

  def createPayzenEvent(self):
    return self.portal.system_event_module.newContent(
        portal_type='Payzen Event',
        reference='PAY-%s' % self.generateNewId())


  def createPayzenSaleInvoiceTransaction(self, destination_section=None, price=2):
    new_title = self.generateNewId()
    new_reference = self.generateNewId()
    new_source_reference = self.generateNewId()
    new_destination_reference = self.generateNewId()
    invoice = self.portal.accounting_module.newContent(
      portal_type="Sale Invoice Transaction",
      title=new_title,
      start_date=DateTime(),
      reference=new_reference,
      source_reference=new_source_reference,
      destination_reference=new_destination_reference,
      destination_section=destination_section,
      payment_mode="payzen",
      specialise="sale_trade_condition_module/slapos_aggregated_trade_condition",
      created_by_builder=1 # to prevent init script to create lines
    )
    self.portal.portal_workflow._jumpToStateFor(invoice, 'stopped')
    invoice.newContent(
      title="",
      portal_type="Invoice Line",
      quantity=-2,
      price=price,
    )
    invoice.newContent(
      portal_type="Sale Invoice Transaction Line",
      source="account_module/receivable",
      quantity=-3,
    )

    payment = self.portal.accounting_module.newContent(
      portal_type="Payment Transaction",
      payment_mode="payzen",
      causality_value=invoice,
      destination_section=destination_section,
      created_by_builder=1 # to prevent init script to create lines
    )
    self.portal.portal_workflow._jumpToStateFor(payment, 'started')
    return invoice

  def createRegularisationRequest(self):
    new_id = self.generateNewId()
    return self.portal.regularisation_request_module.newContent(
      portal_type='Regularisation Request',
      title="Test Reg. Req.%s" % new_id,
      reference="TESTREGREQ-%s" % new_id,
      resource='foo/bar',
      )

class SlapOSTestCaseMixinWithAbort(SlapOSTestCaseMixin):
  abort_transaction = 1
