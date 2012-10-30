# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
    testSlapOSMixin
import transaction
from Products.ERP5Type.tests.backportUnittest import expectedFailure


class TestSlapOSCoreSoftwareInstanceRequest(testSlapOSMixin):

  def afterSetUp(self):
    super(TestSlapOSCoreSoftwareInstanceRequest, self).afterSetUp()
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    self.request_kw = dict(
        software_release=self.generateNewSoftwareReleaseUrl(),
        software_title=self.generateNewSoftwareTitle(),
        software_type=self.generateNewSoftwareType(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        shared=False,
        state="started"
    )

    # prepare part of tree
    hosting_subscription = portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    self.software_instance = portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)

    hosting_subscription.edit(
        title=self.request_kw['software_title'],
        reference="TESTHS-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        root_slave=self.request_kw['shared'],
        predecessor=self.software_instance.getRelativeUrl()
    )
    hosting_subscription.validate()
    self.portal.portal_workflow._jumpToStateFor(hosting_subscription, 'start_requested')

    self.software_instance.edit(
        title=self.request_kw['software_title'],
        reference="TESTSI-%s" % new_id,
        url_string=self.request_kw['software_release'],
        source_reference=self.request_kw['software_type'],
        text_content=self.request_kw['instance_xml'],
        sla_xml=self.request_kw['sla_xml'],
        specialise=hosting_subscription.getRelativeUrl()
    )
    self.portal.portal_workflow._jumpToStateFor(self.software_instance, 'start_requested')
    self.software_instance.validate()
    self.tic()

    # Login as new Software Instance
    self.login(self.software_instance.getReference())

  def beforeTearDown(self):
    transaction.abort()
    if 'request_instance' in self.software_instance.REQUEST:
      self.software_instance.REQUEST['request_instance'] = None

  def test_request_requiredParameter(self):
    good_request_kw = self.request_kw.copy()
    # in order to have unique requested title
    good_request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**good_request_kw)

    # substract parameters
    request_kw = good_request_kw.copy()
    request_kw.pop('software_release')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('software_title')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('software_type')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('instance_xml')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('sla_xml')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('shared')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

    request_kw = good_request_kw.copy()
    request_kw.pop('state')
    self.assertRaises(KeyError, self.software_instance.requestInstance,
                      **request_kw)

  def test_request_createdInstance(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
                     requested_instance.getTitle())
    self.assertEqual('Software Instance',
                     requested_instance.getPortalType())
    self.assertEqual('validated',
                     requested_instance.getValidationState())
    self.assertEqual('start_requested',
                     requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
                     requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
                     requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
                     requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
                     requested_instance.getSourceReference())

  def test_request_sameTitle(self):
    # check that correct request does not raise
    self.assertRaises(ValueError, self.software_instance.requestInstance,
                      **self.request_kw)

  def test_request_shared_True(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
                     requested_instance.getTitle())
    self.assertEqual('Slave Instance',
                     requested_instance.getPortalType())
    self.assertEqual('validated',
                     requested_instance.getValidationState())
    self.assertEqual('start_requested',
                     requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
                     requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
                     requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
                     requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
                     requested_instance.getSourceReference())

  def test_request_shared_unsupported(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = 'True'

    self.assertRaises(ValueError, self.software_instance.requestInstance,
                      **request_kw)

  def test_request_unindexed(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
        requested_instance.getTitle())
    self.assertEqual('Software Instance',
        requested_instance.getPortalType())
    self.assertEqual('validated',
        requested_instance.getValidationState())
    self.assertEqual('start_requested',
        requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())

    transaction.commit()

    self.assertRaises(NotImplementedError, self.software_instance.requestInstance,
        **request_kw)

  def test_request_double(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
        requested_instance.getTitle())
    self.assertEqual('Software Instance',
        requested_instance.getPortalType())
    self.assertEqual('validated',
        requested_instance.getValidationState())
    self.assertEqual('start_requested',
        requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())

    self.tic()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance2)
    self.assertEqual(requested_instance2.getRelativeUrl(),
      requested_instance.getRelativeUrl())

    self.assertEqual(request_kw['software_title'],
        requested_instance2.getTitle())
    self.assertEqual('Software Instance',
        requested_instance2.getPortalType())
    self.assertEqual('validated',
        requested_instance2.getValidationState())
    self.assertEqual('start_requested',
        requested_instance2.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance2.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance2.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance2.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance2.getSourceReference())

  def test_request_duplicated(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    duplicate = self.software_instance.Base_createCloneDocument(batch_mode=1)
    duplicate.edit(
        reference='TESTSI-%s' % self.generateNewId(),
        title=request_kw['software_title'])
    duplicate.validate()
    self.portal.portal_workflow._jumpToStateFor(duplicate, 'start_requested')

    duplicate2 = self.software_instance.Base_createCloneDocument(batch_mode=1)
    duplicate2.edit(
        reference='TESTSI-%s' % self.generateNewId(),
        title=request_kw['software_title'])
    duplicate2.validate()
    self.portal.portal_workflow._jumpToStateFor(duplicate2, 'start_requested')

    self.software_instance.getSpecialiseValue(
        portal_type='Hosting Subscription').edit(
            predecessor_list=[
                duplicate.getRelativeUrl(),
                duplicate2.getRelativeUrl(),
                self.software_instance.getRelativeUrl()
            ]
        )
    self.tic()

    self.assertRaises(ValueError, self.software_instance.requestInstance,
        **request_kw)

  def test_request_destroyed_state(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['state'] = 'destroyed'

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    # requesting with destroyed state shall not create new instance
    self.assertEqual(None, requested_instance)

  def test_request_two_different(self):
    request_kw = self.request_kw.copy()
    # in order to have unique requested title
    request_kw['software_title'] = self.generateNewSoftwareTitle()

    # check that correct request does not raise
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()

    self.software_instance.requestInstance(**request_kw)

    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')

    self.assertNotEqual(requested_instance.getRelativeUrl(),
      requested_instance2.getRelativeUrl())

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl()])

  def test_request_tree_change_indexed(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree shall change to:

    A
    |
    A
    |
    B
    |
    C"""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.tic() # in order to recalculate tree

    B_instance.requestInstance(**request_kw)
    C1_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertEqual(C_instance.getRelativeUrl(), C1_instance.getRelativeUrl())

    self.assertSameSet(self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl()])
    self.assertSameSet(B_instance.getPredecessorList(),
        [C_instance.getRelativeUrl()])

  def test_request_tree_change_not_indexed(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in next transaction, but before indexation,
    the system shall disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    transaction.commit()

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  @expectedFailure
  def test_request_tree_change_same_transaction(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in the same transaction the system shall
    disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  def test_request_started_stopped_destroyed(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance)

    self.assertEqual(request_kw['software_title'],
        requested_instance.getTitle())
    self.assertEqual('Software Instance',
        requested_instance.getPortalType())
    self.assertEqual('validated',
        requested_instance.getValidationState())
    self.assertEqual('start_requested',
        requested_instance.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())

    self.tic()

    request_kw['state'] = 'stopped'
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertNotEqual(None, requested_instance2)
    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())

    self.assertEqual(request_kw['software_title'],
        requested_instance2.getTitle())
    self.assertEqual('Software Instance',
        requested_instance2.getPortalType())
    self.assertEqual('validated',
        requested_instance2.getValidationState())
    self.assertEqual('stop_requested',
        requested_instance2.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance2.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance2.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance2.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance2.getSourceReference())

    self.tic()

    request_kw['state'] = 'destroyed'
    self.software_instance.requestInstance(**request_kw)
    requested_instance3 = self.software_instance.REQUEST.get(
        'request_instance')
    self.assertEqual(None, requested_instance3)

    # in case of destruction instance is not returned, so fetch it
    # directly form document
    requested_instance3 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')
    self.assertEqual(request_kw['software_title'],
        requested_instance3.getTitle())
    self.assertEqual('Software Instance',
        requested_instance3.getPortalType())
    self.assertEqual('validated',
        requested_instance3.getValidationState())
    self.assertEqual('destroy_requested',
        requested_instance3.getSlapState())
    self.assertEqual(request_kw['software_release'],
        requested_instance3.getUrlString())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance3.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance3.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance3.getSourceReference())

  def _countBang(self, document):
    return len([q for q in document.workflow_history[
        'instance_slap_interface_workflow'] if q['action'] == 'bang'])

  def test_request_started_no_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')
    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(bang_amount, self._countBang(requested_instance))

  def test_request_stopped_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['state'] = 'stopped'
    self.software_instance.requestInstance(**request_kw)
    transaction.commit()
    requested_instance2 = self.software_instance.REQUEST.get(
        'request_instance')

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_destroyed_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['state'] = 'destroyed'
    self.software_instance.requestInstance(**request_kw)
    transaction.commit()
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_tree_change_indexed_shared(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree shall change to:

    A
    |
    A
    |
    B
    |
    C"""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.tic() # in order to recalculate tree

    B_instance.requestInstance(**request_kw)
    C1_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertEqual(C_instance.getRelativeUrl(), C1_instance.getRelativeUrl())

    self.assertSameSet(self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl()])
    self.assertSameSet(B_instance.getPredecessorList(),
        [C_instance.getRelativeUrl()])

  def test_request_tree_change_not_indexed_shared(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in next transaction, but before indexation,
    the system shall disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    transaction.commit()

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  @expectedFailure
  def test_request_tree_change_same_transaction_shared(self):
    """Checks tree change forced by request

    For a tree like:

    A
    |
    A
    |\
    B C

    When B requests C tree in the same transaction the system shall
    disallow the operation."""
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    request_kw['shared'] = True
    self.software_instance.requestInstance(**request_kw)
    B_instance = self.software_instance.REQUEST.get('request_instance')

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)
    C_instance = self.software_instance.REQUEST.get('request_instance')

    self.assertSameSet(
        self.software_instance.getPredecessorList(),
        [B_instance.getRelativeUrl(), C_instance.getRelativeUrl()])

    self.assertRaises(NotImplementedError, B_instance.requestInstance,
        **request_kw)

  def test_request_software_release_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['software_release'] = self.generateNewSoftwareReleaseUrl()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['software_release'],
        requested_instance2.getUrlString())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_software_type_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['software_type'] = self.generateNewSoftwareReleaseUrl()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['software_type'],
        requested_instance2.getSourceReference())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_instance_xml_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['instance_xml'] = self.generateSafeXml()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance2.getTextContent())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))

  def test_request_sla_xml_bang(self):
    request_kw = self.request_kw.copy()

    request_kw['software_title'] = self.generateNewSoftwareTitle()
    self.software_instance.requestInstance(**request_kw)

    requested_instance = self.software_instance.REQUEST.get(
        'request_instance')

    self.tic()

    bang_amount = self._countBang(requested_instance)

    request_kw['sla_xml'] = self.generateSafeXml()
    self.software_instance.requestInstance(**request_kw)
    requested_instance2 = self.software_instance.getPredecessorValue(
        portal_type='Software Instance')

    transaction.commit()

    self.assertEqual(requested_instance.getRelativeUrl(),
        requested_instance2.getRelativeUrl())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance2.getSlaXml())
    self.assertEqual(bang_amount+1, self._countBang(requested_instance))
