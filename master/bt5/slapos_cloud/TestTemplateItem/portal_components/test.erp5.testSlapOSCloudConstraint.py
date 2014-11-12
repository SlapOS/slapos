# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import transaction

class TestSlapOSConstraintMixin(testSlapOSMixin):
  @staticmethod
  def getMessageList(o):
    return [str(q.getMessage()) for q in o.checkConsistency()]

  def _test_property_existence(self, obj, property_id, consistency_message,
      value='A', empty_string=True):
    obj.edit(**{property_id:value})

    # fetch basic list of consistency messages
    current_message_list = self.getMessageList(obj)

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)


    # required
    try:
      # try to drop property from object for ones, where doing
      # edit(property=None) does not set None, but ('None',)...
      delattr(obj, property_id)
    except AttributeError:
      # ...but in case of magic ones (reference->default_reference)
      # use setter to set it to None
      obj.edit(**{property_id:None})
    self.assertTrue(consistency_message in self.getMessageList(obj))

    if empty_string:
      obj.edit(**{property_id:''})
      self.assertTrue(consistency_message in self.getMessageList(obj))

    obj.edit(**{property_id:value})
    self.assertFalse(consistency_message in self.getMessageList(obj))
    self.assertSameSet(current_message_list, self.getMessageList(obj))

class TestSlapOSComputerPartitionConstraint(TestSlapOSConstraintMixin):
  def test_non_busy_partition_has_no_related_instance(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    partition = computer.newContent(portal_type='Computer Partition')
    self.portal.portal_workflow._jumpToStateFor(partition, 'free')
    software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    slave_instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance')

    partition.immediateReindexObject()
    software_instance.immediateReindexObject()
    slave_instance.immediateReindexObject()

    consistency_message = "Arity Error for Relation ['default_aggregate'], " \
        "arity is equal to 1 but should be between 0 and 0"

    # test the test: no expected message found
    current_message_list = self.getMessageList(partition)
    self.assertFalse(consistency_message in current_message_list)

    # check case for Software Instance
    software_instance.setAggregate(partition.getRelativeUrl())
    software_instance.immediateReindexObject()
    self.assertTrue(consistency_message in self.getMessageList(partition))
    self.portal.portal_workflow._jumpToStateFor(partition, 'busy')
    self.assertFalse(consistency_message in self.getMessageList(partition))
    self.portal.portal_workflow._jumpToStateFor(partition, 'free')
    software_instance.setAggregate(None)
    software_instance.immediateReindexObject()

    # check case fo Slave Instance
    slave_instance.setAggregate(partition.getRelativeUrl())
    slave_instance.immediateReindexObject()
    self.assertTrue(consistency_message in self.getMessageList(partition))
    self.portal.portal_workflow._jumpToStateFor(partition, 'busy')
    self.assertFalse(consistency_message in self.getMessageList(partition))
    self.portal.portal_workflow._jumpToStateFor(partition, 'free')

  def test_busy_partition_has_one_related_instance(self):
    computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    partition = computer.newContent(portal_type='Computer Partition')
    self.portal.portal_workflow._jumpToStateFor(partition, 'busy')
    software_instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    software_instance.edit(aggregate=partition.getRelativeUrl())
    software_instance_2 = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    slave_instance = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance')
    slave_instance_2 = self.portal.software_instance_module.newContent(
        portal_type='Slave Instance')

    partition.immediateReindexObject()
    software_instance.immediateReindexObject()
    software_instance_2.immediateReindexObject()
    slave_instance.immediateReindexObject()
    slave_instance_2.immediateReindexObject()

    consistency_message = "Arity Error for Relation ['default_aggregate'], " \
        "arity is equal to 0 but should be between 1 and 1"

    # test the test: no expected message found
    current_message_list = self.getMessageList(partition)
    self.assertFalse(consistency_message in current_message_list)

    # check case for Software Instance
    software_instance.edit(aggregate=None)
    software_instance.immediateReindexObject()
    self.assertTrue(consistency_message in self.getMessageList(partition))

    # check case for many Software Instance
    software_instance.edit(aggregate=partition.getRelativeUrl())
    software_instance_2.edit(aggregate=partition.getRelativeUrl())
    software_instance.immediateReindexObject()
    software_instance_2.immediateReindexObject()
    consistency_message_2 = "Arity Error for Relation ['default_aggregate'], " \
        "arity is equal to 2 but should be between 1 and 1"
    self.assertTrue(consistency_message_2 in self.getMessageList(partition))

    # check case for many Slave Instane
    software_instance_2.edit(aggregate=None)
    software_instance_2.immediateReindexObject()
    slave_instance.edit(aggregate=partition.getRelativeUrl())
    slave_instance_2.edit(aggregate=partition.getRelativeUrl())
    slave_instance.immediateReindexObject()
    slave_instance_2.immediateReindexObject()
    self.assertFalse(consistency_message in self.getMessageList(partition))
    self.assertFalse(consistency_message_2 in self.getMessageList(partition))

class TestSlapOSSoftwareInstanceConstraint(TestSlapOSConstraintMixin):
  def afterSetUp(self):
    self.software_instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance')

  def beforeTearDown(self):
    transaction.abort()

  def test_connection_xml(self):
    # fetch basic list of consistency messages
    current_message_list = self.getMessageList(self.software_instance)

    consistency_message = "Connection XML is invalid: Start tag expected, '<' not "\
        "found, line 1, column 1"

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)


    # connection_xml is optional
    self.software_instance.edit(connection_xml=None)
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    self.software_instance.edit(connection_xml='')
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    # if available shall be correct XML
    self.software_instance.edit(connection_xml='this is bad xml')
    self.assertTrue(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(connection_xml=self.generateEmptyXml())
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

  def test_property_existence_destination_reference(self):
    self._test_property_existence(self.software_instance,
        'destination_reference',
        'Property existence error for property destination_reference, this document'
        ' has no such property or the property has never been set')

  def test_property_existence_source_reference(self):
    property_id = 'source_reference'
    consistency_message = 'Property existence error for property '\
        'source_reference, this document has no such property or the property '\
        'has never been set'
    # not required in draft state
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'start_requested')
    self._test_property_existence(self.software_instance,property_id,
        consistency_message)

  def test_property_existence_reference(self):
    self._test_property_existence(self.software_instance, 'reference',
        'Property existence error for property reference, this document'
        ' has no such property or the property has never been set')

  def test_property_existence_ssl_certificate(self):
    property_id = 'ssl_certificate'
    consistency_message = 'Property existence error for property '\
        'ssl_certificate, this document has no such property or the property'\
        ' has never been set'
    self._test_property_existence(self.software_instance, property_id,
        consistency_message)
    # not required in destroy_requested state
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

  def test_property_existence_ssl_key(self):
    property_id = 'ssl_key'
    consistency_message = 'Property existence error for property '\
        'ssl_key, this document has no such property or the property'\
        ' has never been set'
    self._test_property_existence(self.software_instance, property_id,
        consistency_message)
    # not required in destroy_requested state
    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'destroy_requested')
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

  def test_predecessor_related(self):
    software_instance2 = self.portal.software_instance_module.newContent(
      portal_type='Software Instance')
    software_instance3 = self.portal.software_instance_module.newContent(
      portal_type='Software Instance')

    # fetch basic list of consistency messages
    current_message_list = self.getMessageList(self.software_instance)

    consistency_message = "There is more then one related predecessor"

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)

    # if too many, it shall cry
    software_instance2.edit(predecessor=self.software_instance.getRelativeUrl())
    software_instance3.edit(predecessor=self.software_instance.getRelativeUrl())
    self.tic()
    self.assertTrue(consistency_message in self.getMessageList(self.software_instance))

    # one is good
    software_instance2.edit(predecessor=None)
    self.tic()
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    # none is good
    software_instance3.edit(predecessor=None)
    self.tic()
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

  def test_sla_xml(self):
    # fetch basic list of consistency messages
    current_message_list = self.getMessageList(self.software_instance)

    consistency_message = "Sla XML is invalid: Start tag expected, '<' not "\
        "found, line 1, column 1"

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)


    # sla_xml is optional
    self.software_instance.edit(sla_xml=None)
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    self.software_instance.edit(sla_xml='')
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    # if available shall be correct XML
    self.software_instance.edit(sla_xml='this is bad xml')
    self.assertTrue(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(sla_xml=self.generateEmptyXml())
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

  def test_text_content(self):
    # fetch basic list of consistency messages
    current_message_list = self.getMessageList(self.software_instance)

    consistency_message = "Instance XML is invalid: Start tag expected, '<' not "\
        "found, line 1, column 1"

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)


    # text_content is optional
    self.software_instance.edit(text_content=None)
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    self.software_instance.edit(text_content='')
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    # if available shall be correct XML
    self.software_instance.edit(text_content='this is bad xml')
    self.assertTrue(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(text_content=self.generateEmptyXml())
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

class TestSlapOSSlaveInstanceConstraint(TestSlapOSConstraintMixin):
  def afterSetUp(self):
    self.software_instance = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance')

  def beforeTearDown(self):
    transaction.abort()

  def test_property_existence_source_reference(self):
    consistency_message = 'Property existence error for property '\
        'source_reference, this document has no such property '\
        'or the property has never been set'
    property_id = 'source_reference'
    # not required in draft state
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'start_requested')
    self._test_property_existence(self.software_instance,
        property_id, consistency_message)

  def test_property_existence_text_content(self):
    consistency_message = 'Property existence error for property '\
        'text_content, this document has no such property '\
        'or the property has never been set'
    property_id = 'text_content'
    # not required in draft state
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'start_requested')
    self._test_property_existence(self.software_instance, property_id,
        consistency_message)

  def test_property_existence_reference(self):
    self._test_property_existence(self.software_instance, 'reference',
        'Property existence error for property reference, this document'
        ' has no such property or the property has never been set')

  def test_predecessor_related(self):
    software_instance2 = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance')
    software_instance3 = self.portal.software_instance_module.newContent(
      portal_type='Slave Instance')

    # fetch basic list of consistency messages
    current_message_list = self.getMessageList(self.software_instance)

    consistency_message = "There is more then one related predecessor"

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)

    # if too many, it shall cry
    software_instance2.edit(predecessor=self.software_instance.getRelativeUrl())
    software_instance3.edit(predecessor=self.software_instance.getRelativeUrl())
    self.tic()
    self.assertTrue(consistency_message in self.getMessageList(self.software_instance))

    # one is good
    software_instance2.edit(predecessor=None)
    self.tic()
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

    # none is good
    software_instance3.edit(predecessor=None)
    self.tic()
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))
    self.assertSameSet(current_message_list, self.getMessageList(self.software_instance))

class TestSlapOSHostingSubscriptionConstraint(TestSlapOSConstraintMixin):
  def afterSetUp(self):
    self.software_instance = self.portal.hosting_subscription_module.newContent(
      portal_type='Hosting Subscription')

  def beforeTearDown(self):
    transaction.abort()

  def test_property_existence_reference(self):
    self._test_property_existence(self.software_instance, 'reference',
        'Property existence error for property reference, this document'
        ' has no such property or the property has never been set')

  def test_property_existence_title(self):
    self._test_property_existence(self.software_instance, 'title',
        'Property existence error for property title, this document'
        ' has no such property or the property has never been set')

  def test_property_existence_source_reference(self):
    property_id = 'source_reference'
    consistency_message = 'Property existence error for property '\
        'source_reference, this document has no such property or the property '\
        'has never been set'
    # not required in draft state
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'start_requested')
    self._test_property_existence(self.software_instance, property_id,
        consistency_message)

  def test_property_existence_root_slave(self):
    property_id = 'root_slave'
    consistency_message = 'Property existence error for property '\
        'root_slave, this document has no such property or the property '\
        'has never been set'
    # not required in draft state
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'start_requested')
    self._test_property_existence(self.software_instance, property_id,
        consistency_message, value=True)

  def test_property_existence_url_string(self):
    property_id = 'url_string'
    consistency_message = 'Property existence error for property '\
        'url_string, this document has no such property or the property '\
        'has never been set'
    # not required in draft state
    self.software_instance.edit(**{property_id:None})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.software_instance.edit(**{property_id:''})
    self.assertFalse(consistency_message in self.getMessageList(self.software_instance))

    self.portal.portal_workflow._jumpToStateFor(self.software_instance,
        'start_requested')
    self._test_property_existence(self.software_instance, property_id,
        consistency_message)

class TestSlapOSPersonConstraint(TestSlapOSConstraintMixin):

  def test_role(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    consistency_message = 'One role should be defined'
    self.assertTrue(consistency_message in self.getMessageList(person))

    role_id_list = list(self.portal.portal_categories.role.objectIds())
    self.assertTrue(len(role_id_list) >= 2)
    person.setRole(role_id_list[0])
    self.assertFalse(consistency_message in self.getMessageList(person))

    person.setRoleList(role_id_list)
    self.assertTrue(consistency_message in self.getMessageList(person))
    person.setRole(role_id_list[0])
    self.assertFalse(consistency_message in self.getMessageList(person))

  def test_subordination_state(self):
    organisation = self.portal.organisation_module.newContent(
      portal_type='Organisation')
    person = self.portal.person_module.newContent(portal_type='Person',
      subordination=organisation.getRelativeUrl())
    consistency_message = 'The Organisation is not validated'

    self.assertTrue(consistency_message in self.getMessageList(person))

    organisation.validate()

    self.assertFalse(consistency_message in self.getMessageList(person))

  def test_email(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    consistency_message = 'Person have to contain an Email'

    self.assertTrue(consistency_message in self.getMessageList(person))

    person.newContent(portal_type='Email')

    self.assertFalse(consistency_message in self.getMessageList(person))

class TestSlapOSAssignmentConstraint(TestSlapOSConstraintMixin):
  def test_parent_person_validated(self):
    person = self.portal.person_module.newContent(portal_type='Person')
    assignment = person.newContent(portal_type='Assignment')

    consistency_message = 'The person document has to be validated to start '\
      'assignment'
    self.assertTrue(consistency_message in self.getMessageList(assignment))

    person.validate()

    self.assertFalse(consistency_message in self.getMessageList(assignment))

class TestSlapOSEmailConstraint(TestSlapOSConstraintMixin):
  def test_url_string_not_empty(self):
    email = self.portal.person_module.newContent(portal_type='Person'
      ).newContent(portal_type='Email')
    consistency_message = 'Email must be defined'

    self.assertTrue(consistency_message in self.getMessageList(email))

    email.setUrlString(self.generateNewId())

    self.assertFalse(consistency_message in self.getMessageList(email))

class TestSlapOSComputerConstraint(TestSlapOSConstraintMixin):
  def test_title_not_empty(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    consistency_message = 'Title must be defined'

    self.assertTrue(consistency_message in self.getMessageList(computer))

    computer.setTitle(self.generateNewId())

    self.assertFalse(consistency_message in self.getMessageList(computer))

  def test_reference_not_empty(self):
    computer = self.portal.computer_module.newContent(portal_type='Computer')
    consistency_message = 'Reference must be defined'

    self.assertTrue(consistency_message in self.getMessageList(computer))

    computer.setReference(self.generateNewId())

    self.assertFalse(consistency_message in self.getMessageList(computer))

  def test_reference_unique(self):
    reference = self.generateNewId()
    reference_2 = self.generateNewId()
    computer = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    computer_2 = self.portal.computer_module.newContent(portal_type='Computer',
      reference=reference)
    consistency_message = 'Reference must be unique'

    self.tic()

    self.assertTrue(consistency_message in self.getMessageList(computer))
    self.assertTrue(consistency_message in self.getMessageList(computer_2))

    computer_2.setReference(reference_2)
    self.tic()

    self.assertFalse(consistency_message in self.getMessageList(computer))
    self.assertFalse(consistency_message in self.getMessageList(computer_2))
