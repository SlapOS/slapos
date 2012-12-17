# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.utils import createZODBPythonScript
from DateTime import DateTime

class TestSlapOSAccountingInteractionWorkflow(testSlapOSMixin):
  def beforeTearDown(self):
    transaction.abort()

  def test_SlaveInstance_changePromise(self):
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      )
    instance.validate()

    self.assertEqual(instance.getCausalityState(), 'diverged')

    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=True,
    )

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.requestStop(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.requestStart(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.bang(comment='Test bang interaction', bang_tree=False)
    self.assertEqual(instance.getCausalityState(), 'diverged')

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.requestDestroy(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

  def test_SlaveInstance_changePromiseInDivergeState(self):
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      )
    instance.validate()

    self.assertEqual(instance.getCausalityState(), 'diverged')

    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=True,
    )

    instance.requestStop(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

  def test_SoftwareInstance_changePromise(self):
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      )
    instance.validate()

    self.assertEqual(instance.getCausalityState(), 'diverged')

    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
    )

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.requestStop(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.requestStart(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.bang(comment='Test bang interaction', bang_tree=False)
    self.assertEqual(instance.getCausalityState(), 'diverged')

    instance.converge()
    self.assertEqual(instance.getCausalityState(), 'solved')
    instance.requestDestroy(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

  def test_SoftwareInstance_changePromiseInDivergedState(self):
    new_id = self.generateNewId()
    instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      destination_reference="TESTINST-%s" % new_id,
      ssl_certificate="foo",
      ssl_key="bar",
      )
    instance.validate()

    self.assertEqual(instance.getCausalityState(), 'diverged')

    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
    )

    instance.requestStop(**request_kw)
    self.assertEqual(instance.getCausalityState(), 'diverged')

  def test_HostingSubscription_fixConsistency(self,
        date=DateTime('2012/01/15'), day=15):
    new_id = self.generateNewId()
    item = self.portal.hosting_subscription_module.newContent(
      portal_type='Hosting Subscription',
      title="Subscription %s" % new_id,
      reference="TESTSUB-%s" % new_id,
      periodicity_hour_list=None,
      periodicity_minute_list=None,
      periodicity_month_day=None,
    )

    self.assertEqual(item.getPeriodicityHour(), None)
    self.assertEqual(item.getPeriodicityMinute(), None)
    self.assertEqual(item.getPeriodicityMonthDay(), None)

    try:
      from Products.ERP5Type.Base import Base
      Base.original_getCreationDate = Base.getCreationDate
      def getCreationDate(*args, **kwargs):
        return date
      Base.getCreationDate = getCreationDate
      item.fixConsistency()
    finally:
      Base.getCreationDate = Base.original_getCreationDate
      delattr(Base, 'original_getCreationDate')

    self.assertEqual(item.getPeriodicityHourList(), [0])
    self.assertEqual(item.getPeriodicityMinuteList(), [0])
    self.assertEqual(item.getPeriodicityMonthDay(), day)

  def test_HostingSubscription_fixConsistency_today_after_28(self):
    self.test_HostingSubscription_fixConsistency(DateTime('2012/01/30'), 28)

  def test_HostingSubscription_manageAfter(self):
    class DummyTestException(Exception):
      pass

    def verify_fixConsistency_call(self):
      # Check that fixConsistency is called on hosting subscription
      if self.getRelativeUrl().startswith('hosting_subscription_module/'):
        raise DummyTestException
      else:
        return self.fixConsistency_call()

    # Replace serialize by a dummy method
    HostingSubscriptionClass = self.portal.portal_types.getPortalTypeClass(
        'Hosting Subscription')
    HostingSubscriptionClass.fixConsistency_call = HostingSubscriptionClass.\
        fixConsistency
    HostingSubscriptionClass.fixConsistency = verify_fixConsistency_call

    try:
      # manage_afterAdd
      self.assertRaises(
        DummyTestException, 
        self.portal.hosting_subscription_module.newContent,
        portal_type='Hosting Subscription')
      # manage_afterClone
      self.assertRaises(
        DummyTestException, 
        self.portal.hosting_subscription_module.\
          template_hosting_subscription.Base_createCloneDocument,
        batch_mode=1)
    finally:
      self.portal.portal_types.resetDynamicDocumentsOnceAtTransactionBoundary()
      transaction.commit()

  def _simulateDelivery_calculate(self):
    script_name = 'Delivery_calculate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      raise ValueError('Precondition failed: %s exists in custom' % script_name)
    createZODBPythonScript(self.portal.portal_skins.custom,
                        script_name,
                        '*args, **kwargs',
                        '# Script body\n'
"""portal_workflow = context.portal_workflow
portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Delivery_calculate') """)
    transaction.commit()

  def _dropDelivery_calculate(self):
    script_name = 'Delivery_calculate'
    if script_name in self.portal.portal_skins.custom.objectIds():
      self.portal.portal_skins.custom.manage_delObjects(script_name)
    transaction.commit()

  def _test_calculate(self, new_id, newContent, **new_kw):
    cancel_spl = newContent(**new_kw)
    close_spl = newContent(**new_kw)
    confirm_spl = newContent(**new_kw)
    deliver_spl = newContent(**new_kw)
    deliver_spl.confirm()
    deliver_spl.stop()
    order_spl = newContent(**new_kw)
    plan_spl = newContent(**new_kw)
    setReady_spl = newContent(**new_kw)
    setReady_spl.confirm()
    start_spl = newContent(**new_kw)
    start_spl.confirm()
    stop_spl = newContent(**new_kw)
    stop_spl.confirm()
    submit_spl = newContent(**new_kw)

    self._simulateDelivery_calculate()
    try:
      cancel_spl.cancel()
      close_spl.close()
      confirm_spl.confirm()
      deliver_spl.deliver()
      order_spl.order()
      plan_spl.plan()
      setReady_spl.setReady()
      start_spl.start()
      stop_spl.stop()
      submit_spl.submit()
    finally:
      self._dropDelivery_calculate()
    self.assertEqual(
      cancel_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      close_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      confirm_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      deliver_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      order_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      plan_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      setReady_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      start_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      stop_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')
    self.assertEqual(
      submit_spl.workflow_history['edit_workflow'][-1]['comment'],
      'Visited by Delivery_calculate')

  def test_SalePackingList_calculate(self):
    new_id = self.generateNewId()
    newContent = self.portal.sale_packing_list_module.newContent
    portal_type = "Sale Packing List"
    self._test_calculate(new_id, newContent, portal_type=portal_type)

  def test_SaleInvoiceTransaction_calculate(self):
    new_id = self.generateNewId()
    newContent = self.portal.accounting_module.newContent
    portal_type = "Sale Invoice Transaction"
    self._test_calculate(new_id, newContent, portal_type=portal_type,
        start_date='2011/01/01')

  def test_HostingSubscription_changePromise(self):
    new_id = self.generateNewId()
    subscription = self.portal.hosting_subscription_module.newContent(
      portal_type='Hosting Subscription',
      title="Subscription %s" % new_id,
      reference="TESTSUB-%s" % new_id,
      )
    subscription.validate()

    self.assertEqual(subscription.getCausalityState(), 'diverged')

    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
    )

    subscription.requestStart(**request_kw)
    subscription.converge()
    self.assertEqual(subscription.getCausalityState(), 'solved')
    subscription.requestDestroy(**request_kw)
    self.assertEqual(subscription.getCausalityState(), 'diverged')

  def test_HostingSubscription_changePromiseInDivergedState(self):
    new_id = self.generateNewId()
    subscription = self.portal.hosting_subscription_module.newContent(
      portal_type='Hosting Subscription',
      title="Subscription %s" % new_id,
      reference="TESTSUB-%s" % new_id,
      )
    subscription.validate()


    request_kw = dict(
      software_release='http://example.org',
      software_type='http://example.org',
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
    )

    subscription.requestStart(**request_kw)
    self.assertEqual(subscription.getCausalityState(), 'diverged')

    subscription.requestDestroy(**request_kw)
    self.assertEqual(subscription.getCausalityState(), 'diverged')
