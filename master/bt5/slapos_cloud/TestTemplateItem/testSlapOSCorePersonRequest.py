# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.Vifib.tests.testVifibSlapWebService import \
  TestVifibSlapWebServiceMixin
import transaction
from Products.ERP5Type.tests.backportUnittest import expectedFailure

class TestSlapOSCorePersonRequest(TestVifibSlapWebServiceMixin):

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/test%s.cfg' % self.generateNewId()

  def afterSetUp(self):
    portal = self.getPortalObject()
    new_id = self.generateNewId()

    self.setupPortalCertificateAuthority()

    # Clone software release document
    software_release = portal.software_release_module.template_software_release.\
                                 Base_createCloneDocument(batch_mode=1)
    software_release.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      url_string=self.generateNewSoftwareReleaseUrl(),
    )
    software_release.publish()
    self.software_release = software_release

    new_id = self.generateNewId()
    software_release = portal.software_release_module.template_software_release.\
                                 Base_createCloneDocument(batch_mode=1)
    software_release.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      url_string=self.generateNewSoftwareReleaseUrl(),
    )
    software_release.publish()
    self.software_release2 = software_release

    # Clone person document
    person_user = portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.updateLocalRolesOnSecurityGroups()
    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    transaction.commit()
    # XXX Tic is needed to reindex the created open order
    self.tic()

    # Login as new user
    self.login(person_user.getReference())
    new_person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
    self.assertEquals(person_user.getRelativeUrl(), new_person.getRelativeUrl())

  def beforeTearDown(self):
    pass

  def test_Person_requestSoftwareInstance_requiredParameter(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    self.assertRaises(TypeError, person.requestSoftwareInstance)

    # software_release is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # software_title is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # software_type is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # instance_xml is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # instance_xml is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

    # sla_xml is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      shared=shared,
      state=state,
    )

    # shared is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      state=state,
    )

    # state is mandatory
    self.assertRaises(TypeError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
    )

  def test_Person_requestSoftwareInstance_acceptedState(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    # Only started, stopped, destroyed
    self.assertRaises(ValueError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="foo",
    )

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title="started",
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="started",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("start_requested", hosting_subscription.getSlapState())

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title="stopped",
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="stopped",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("stop_requested", hosting_subscription.getSlapState())

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title="destroyed",
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="destroyed",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(None, hosting_subscription)

  def test_Person_requestSoftwareInstance_returnHostingSubscriptionUrl(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("Hosting Subscription", 
                      hosting_subscription.getPortalType())

  def test_Person_requestSoftwareInstance_createHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    previous_id = self.getPortalObject().portal_ids\
        .generateNewId(id_group='slap_hosting_subscription_reference', 
                       id_generator='uid')

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(software_release, 
                      hosting_subscription.getRootSoftwareReleaseUrl())
    self.assertEquals(software_title, hosting_subscription.getTitle())
    self.assertEquals(software_type, hosting_subscription.getSourceReference())
    self.assertEquals(instance_xml, hosting_subscription.getTextContent())
    self.assertEquals(sla_xml, hosting_subscription.getSlaXml())
    self.assertEquals(shared, hosting_subscription.getRootSlave())
    self.assertEquals("start_requested", hosting_subscription.getSlapState())
    self.assertEquals("HOSTSUBS-%s" % (previous_id+1),
                      hosting_subscription.getReference())
    self.assertEquals("validated", hosting_subscription.getValidationState())

  def test_Person_requestSoftwareInstance_HostingSubscriptionNotReindexed(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    transaction.commit()

    self.assertRaises(NotImplementedError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

  @expectedFailure
  def test_Person_requestSoftwareInstance_updateHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    hosting_subscription_reference = hosting_subscription.getReference()

    transaction.commit()
    self.tic()

    software_release2 = self.software_release.getUrlString()
    software_type2 = "test2"
    instance_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    sla_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    shared2 = False
    state2 = "stopped"

    person.requestSoftwareInstance(
      software_release=software_release2,
      software_title=software_title,
      software_type=software_type2,
      instance_xml=instance_xml2,
      sla_xml=sla_xml2,
      shared=shared2,
      state=state2,
    )

    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(hosting_subscription.getRelativeUrl(),
                      hosting_subscription2.getRelativeUrl())
    self.assertEquals(hosting_subscription_reference,
                      hosting_subscription2.getReference())

    self.assertEquals(software_release2, 
                      hosting_subscription.getRootSoftwareReleaseUrl())
    self.assertEquals(software_title, hosting_subscription.getTitle())
    self.assertEquals(software_type2, hosting_subscription.getSourceReference())
    self.assertEquals(instance_xml2, hosting_subscription.getTextContent())
    self.assertEquals(sla_xml2, hosting_subscription.getSlaXml())
    self.assertEquals(shared2, hosting_subscription.getRootSlave())
    self.assertEquals("stop_requested", hosting_subscription.getSlapState())
    self.assertEquals("validated", hosting_subscription.getValidationState())

  def test_Person_requestSoftwareInstance_duplicatedHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    hosting_subscription.updateLocalRolesOnSecurityGroups()
    transaction.commit()
    hosting_subscription2 = hosting_subscription.Base_createCloneDocument(
                                                                batch_mode=1)
    hosting_subscription2.validate()

    transaction.commit()
    self.tic()

    self.assertRaises(NotImplementedError, person.requestSoftwareInstance,
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )

  def test_Person_requestSoftwareInstance_HostingSubscriptionNewTitle(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version='1.0' encoding='utf-8'?>
<instance>
</instance>"""
    sla_xml = """<?xml version='1.0' encoding='utf-8'?>
<instance>
</instance>"""
    shared = True
    state = "started"

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state=state,
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')

    transaction.commit()

    software_release2 = self.software_release.getUrlString()
    software_title2 = "test2"
    software_type2 = "test2"
    instance_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    sla_xml2 = """<?xml version='1.0' encoding='utf-8'?>
<instance>

</instance>"""
    shared2 = False
    state2 = "stopped"

    person.requestSoftwareInstance(
      software_release=software_release2,
      software_title=software_title2,
      software_type=software_type2,
      instance_xml=instance_xml2,
      sla_xml=sla_xml2,
      shared=shared2,
      state=state2,
    )

    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertNotEquals(hosting_subscription.getRelativeUrl(),
                      hosting_subscription2.getRelativeUrl())
    self.assertNotEquals(hosting_subscription.getReference(),
                      hosting_subscription2.getReference())

    self.assertEquals(software_release2, 
                      hosting_subscription2.getRootSoftwareReleaseUrl())
    self.assertEquals(software_title2, hosting_subscription2.getTitle())
    self.assertEquals(software_type2, hosting_subscription2.getSourceReference())
    self.assertEquals(instance_xml2, hosting_subscription2.getTextContent())
    self.assertEquals(sla_xml2, hosting_subscription2.getSlaXml())
    self.assertEquals(shared2, hosting_subscription2.getRootSlave())
    self.assertEquals("stop_requested", hosting_subscription2.getSlapState())
    self.assertEquals("validated", hosting_subscription2.getValidationState())

  def test_Person_requestSoftwareInstance_deletedHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="stopped",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    transaction.commit()
    self.tic()

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="destroyed",
    )
    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals(None, hosting_subscription2)
    self.assertEquals("destroy_requested", hosting_subscription.getSlapState())

  def test_Person_requestSoftwareInstance_noConflictWithDeletedHostingSubscription(self):
    person = self.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

    software_release = self.software_release.getUrlString()
    software_title = "test"
    software_type = "test"
    instance_xml = """<?xml version="1.0" encoding="utf-8"?>
    <instance>
    </instance>
    """
    sla_xml = "test"
    shared = True

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="stopped",
    )
    hosting_subscription = person.REQUEST.get('request_hosting_subscription')
    transaction.commit()
    self.tic()
    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="destroyed",
    )
    self.assertEquals("destroy_requested", hosting_subscription.getSlapState())
    transaction.commit()
    self.tic()

    person.requestSoftwareInstance(
      software_release=software_release,
      software_title=software_title,
      software_type=software_type,
      instance_xml=instance_xml,
      sla_xml=sla_xml,
      shared=shared,
      state="started",
    )
    hosting_subscription2 = person.REQUEST.get('request_hosting_subscription')
    self.assertEquals("start_requested", hosting_subscription2.getSlapState())
    self.assertNotEquals(hosting_subscription.getRelativeUrl(), 
                         hosting_subscription2.getRelativeUrl())
