# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction

class TestSlapOSCoreSoftwareInstanceRequest(testSlapOSMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/test%s.cfg' % self.generateNewId()

  def generateNewSoftwareType(self):
    return 'Type%s' % self.generateNewId()

  def generateNewSoftwareTitle(self):
    return 'Title%s' % self.generateNewId()

  def afterSetUp(self):
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    self.setupPortalCertificateAuthority()

    safe_xml = '<?xml version="1.0" encoding="utf-8"?><instance></instance>'
    title = self.generateNewSoftwareTitle()
    self.request_kw = dict(
        software_release=self.generateNewSoftwareReleaseUrl(),
        software_title=title,
        software_type=self.generateNewSoftwareType(),
        instance_xml=safe_xml,
        sla_xml=safe_xml,
        shared=False,
        state="started"
    )

    # prepare part of tree
    hosting_subscription = portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)

    hosting_subscription.edit(
        title=title,
        reference="TESTHS-%s" % new_id
    )
    hosting_subscription.updateLocalRolesOnSecurityGroups()
    hosting_subscription.validate()
    hosting_subscription.requestStart(**self.request_kw)
    hosting_subscription.requestInstance(**self.request_kw)

    self.software_instance = hosting_subscription.getPredecessorValue(
        portal_type='Software Instance')
    self.tic()

    # Login as new Software Instance
    self.login(self.software_instance.getReference())

  def beforeTearDown(self):
    pass

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
        requested_instance.getRootSoftwareReleaseUrl())
    self.assertEqual(request_kw['instance_xml'],
        requested_instance.getTextContent())
    self.assertEqual(request_kw['sla_xml'],
        requested_instance.getSlaXml())
    self.assertEqual(request_kw['software_type'],
        requested_instance.getSourceReference())
