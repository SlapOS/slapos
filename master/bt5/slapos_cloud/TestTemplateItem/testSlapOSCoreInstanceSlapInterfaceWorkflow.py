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
    self.request_kw = dict(
      software_release=\
          self.generateNewSoftwareReleaseUrl(),
      software_type=self.generateNewSoftwareType(),
      instance_xml=self.generateSafeXml(),
      sla_xml=self.generateSafeXml(),
      shared=False,
      software_title=hosting_subscription.getTitle(),
      state='started'
    )
    hosting_subscription.requestStart(**self.request_kw)
    hosting_subscription.requestInstance(**self.request_kw)

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
    request_kw = self.request_kw.copy()
    request_kw['software_title'] = 'New %s' % self.generateNewId()
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

  def test_rename_new_name_required(self):
    self.login(self.instance.getReference())
    self.assertRaises(KeyError, self.instance.rename)

  def test_rename(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())
    self.instance.rename(new_name=new_name)
    self.assertEqual(new_name, self.instance.getTitle())
    transaction.abort()

  def test_rename_twice_not_indexed(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())
    self.instance.rename(new_name=new_name)
    self.assertEqual(new_name, self.instance.getTitle())
    transaction.commit()
    self.assertRaises(NotImplementedError, self.instance.rename,
        new_name=new_name)
    transaction.abort()

  @expectedFailure
  def test_rename_twice_same_transaction(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())
    self.instance.rename(new_name=new_name)
    self.assertEqual(new_name, self.instance.getTitle())
    self.assertRaises(NotImplementedError, self.instance.rename,
        new_name=new_name)
    transaction.abort()

  def test_rename_existing(self):
    new_name = 'New %s' % self.generateNewId()
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    request_kw['software_title'] = new_name

    self.instance.requestInstance(**request_kw)
    request_instance = self.instance.REQUEST['request_instance']
    self.instance.REQUEST['request_instance'] = None
    # test sanity check
    self.assertEqual(new_name, request_instance.getTitle())
    self.tic()

    self.assertRaises(ValueError, self.instance.rename, new_name=new_name)
    transaction.abort()

  def test_requestDestroy(self):
    self.login(self.instance.getReference())

    request_kw = self.request_kw.copy()
    self.instance.requestDestroy(**request_kw)
    self.assertEqual('destroy_requested', self.instance.getSlapState())
    transaction.abort()

  def test_requestDestroy_required(self):
    self.login(self.instance.getReference())

    software_release=self.request_kw['software_release']
    software_type=self.request_kw['software_type']
    instance_xml=self.request_kw['instance_xml']
    sla_xml=self.request_kw['sla_xml']
    shared=self.request_kw['shared']

    self.assertRaises(TypeError, self.instance.requestDestroy)
    transaction.abort()

    # no software_release
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no software_type
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no instance_xml
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
    )
    transaction.abort()

    # no shared
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
    )
    transaction.abort()
    
    # no sla_xml
    self.assertRaises(TypeError, self.instance.requestDestroy,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      shared=shared,
    )
    transaction.abort()
