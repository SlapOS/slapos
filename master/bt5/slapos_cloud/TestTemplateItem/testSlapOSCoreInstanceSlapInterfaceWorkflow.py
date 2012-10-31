# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction
from Products.ERP5Type.tests.backportUnittest import expectedFailure

class TestSlapOSCoreInstanceSlapInterfaceWorkflow(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSlapOSCoreInstanceSlapInterfaceWorkflow, self).afterSetUp()

    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
    )
    hosting_subscription.validate()
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**kw)
    hosting_subscription.requestInstance(**kw)

    self.instance = hosting_subscription.getPredecessorValue()
    self.tic()

  def _countInstanceBang(self, instance, comment):
    return len([q for q in instance.workflow_history[
        'instance_slap_interface_workflow'] if q['action'] == 'bang' and \
            q['comment'] == comment])

  def test_bang_required_comment(self):
    self.login(self.instance.getReference())
    self.assertRaises(KeyError, self.instance.bang, bang_tree=0)
    transaction.abort()

  def test_bang_required_bang_tree(self):
    self.login(self.instance.getReference())
    comment = 'Comment %s' % self.generateNewId()
    self.assertRaises(KeyError, self.instance.bang, comment=comment)
    transaction.abort()

  def test_bang(self):
    self.login(self.instance.getReference())
    comment = 'Comment %s' % self.generateNewId()
    count = self._countInstanceBang(self.instance, comment)
    self.instance.bang(bang_tree=0, comment=comment)
    self.assertEqual(count+1, self._countInstanceBang(self.instance, comment))

  def test_bang_tree(self):
    self.login(self.instance.getReference())
    request_kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title='New %s' % self.generateNewId(),
      state='started'
    )
    self.instance.requestInstance(**request_kw)
    request_instance = self.instance.REQUEST['request_instance']
    self.instance.REQUEST['request_instance'] = None
    self.tic()

    comment = 'Comment %s' % self.generateNewId()
    count1 = self._countInstanceBang(self.instance, comment)
    count2 = self._countInstanceBang(request_instance, comment)
    self.instance.bang(bang_tree=1, comment=comment)
    self.tic()
    self.assertEqual(count1+1, self._countInstanceBang(self.instance,
        comment))
    self.assertEqual(count2+1, self._countInstanceBang(request_instance,
        comment))

  def test_allocatePartition_computer_partition_url_required(self):
    self.login(self.instance.getReference())
    self.assertRaises(TypeError, self.instance.allocatePartition)

  def test_allocatePartition(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    computer.validate()
    computer_partition = computer.newContent(portal_type='Computer Partition')
    computer_partition.validate()
    computer_partition.markFree()
    computer_partition_url = computer_partition.getRelativeUrl()
    self.instance.allocatePartition(
        computer_partition_url=computer_partition_url)
    self.assertEqual(self.instance.getAggregate(), computer_partition_url)
