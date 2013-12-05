# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from zExceptions import Unauthorized
from DateTime import DateTime
from functools import wraps
from Products.ERP5Type.tests.utils import createZODBPythonScript
import difflib

class TestSlapOSSoftwareInstance_requestValidationPayment(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createCloudContract(self):
    new_id = self.generateNewId()
    contract = self.portal.cloud_contract_module.newContent(
      portal_type='Cloud Contract',
      title="Contract %s" % new_id,
      reference="TESTCONTRACT-%s" % new_id,
      )
    self.portal.portal_workflow._jumpToStateFor(contract, 'invalidated')
    return contract

  def createPaymentTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Payment Transaction',
      title="Payment %s" % new_id,
      reference="TESTPAY-%s" % new_id,
      )

  def createInvoiceTransaction(self):
    new_id = self.generateNewId()
    return self.portal.accounting_module.newContent(
      portal_type='Sale Invoice Transaction',
      title="Invoice %s" % new_id,
      reference="TESTINV-%s" % new_id,
      created_by_builder=1,
      )

  def createNeededDocuments(self):
    new_id = self.generateNewId()
    person = self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      )
    subscription = self.portal.hosting_subscription_module.newContent(
      portal_type='Hosting Subscription',
      title="Subscription %s" % new_id,
      reference="TESTSUB-%s" % new_id,
      destination_section_value=person,
      )
    instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance',
      title="Instance %s" % new_id,
      reference="TESTINST-%s" % new_id,
      specialise_value=subscription,
      )
    return person, instance, subscription

  def test_requestValidationPayment_REQUEST_disallowed(self):
    person, instance, subscription = self.createNeededDocuments()
    self.assertRaises(
      Unauthorized,
      instance.SoftwareInstance_requestValidationPayment,
      REQUEST={})

  def test_prevent_concurrency(self):
    person, instance, subscription = self.createNeededDocuments()
    tag = "%s_requestValidationPayment_inProgress" % person.getUid()
    person.reindexObject(activate_kw={'tag': tag})
    transaction.commit()

    result = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(result, None)

  def test_addCloudContract(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = instance.SoftwareInstance_requestValidationPayment()

    # Default property
    self.assertEquals(contract.getPortalType(), 'Cloud Contract')
    self.assertEquals(contract.getValidationState(), 'invalidated')
    self.assertEquals(contract.getDestinationSection(), person.getRelativeUrl())
    self.assertEquals(contract.getTitle(),
           'Contract for "%s"' % person.getTitle())

  def test_addCloudContract_do_not_duplicate_contract_if_not_reindexed(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = instance.SoftwareInstance_requestValidationPayment()
    transaction.commit()
    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertNotEquals(contract, None)
    self.assertEquals(contract2, None)

  def test_addCloudContract_existing_invalidated_contract(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = instance.SoftwareInstance_requestValidationPayment()
    transaction.commit()
    self.tic()
    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertNotEquals(contract, None)
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())

  def test_addCloudContract_existing_validated_contract(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = instance.SoftwareInstance_requestValidationPayment()
    contract.validate()
    transaction.commit()
    self.tic()
    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertNotEquals(contract, None)
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())

  def test_do_nothing_if_validated_contract(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    contract.edit(destination_section_value=person)
    contract.validate()
    self.tic()

    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertEquals(contract2.getCausality(""), "")
    self.assertEquals(contract2.getValidationState(), "validated")

  def test_validate_contract_if_payment_found(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    contract.edit(destination_section_value=person)
    payment = self.createPaymentTransaction()
    payment.edit(
      default_destination_section_value=person,
    )
    self.portal.portal_workflow._jumpToStateFor(payment, 'stopped')
    self.assertEquals(contract.getValidationState(), "invalidated")
    self.tic()

    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertEquals(contract2.getCausality(""), "")
    self.assertEquals(contract2.getValidationState(), "validated")

  def test_create_invoice_if_needed_and_no_payment_found(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    contract.edit(destination_section_value=person)
    self.assertEquals(contract.getValidationState(), "invalidated")
    self.tic()

    before_date = DateTime()
    contract2 = instance.SoftwareInstance_requestValidationPayment()
    after_date = DateTime()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertNotEquals(contract2.getCausality(""), "")
    self.assertEquals(contract2.getValidationState(), "invalidated")

    invoice = contract2.getCausalityValue()
    self.assertEquals(invoice.getPortalType(), 'Sale Invoice Transaction')
    self.assertEquals(len(invoice.contentValues()), 1)
    self.assertEquals(invoice.getSimulationState(), 'confirmed')
    self.assertEquals(invoice.getCausalityState(), 'building')
    self.assertEquals(invoice.getTitle(), 'Account validation')
    self.assertEquals(invoice.getSource(), person.getRelativeUrl())
    self.assertEquals(invoice.getDestination(), person.getRelativeUrl())
    self.assertEquals(invoice.getDestinationSection(), person.getRelativeUrl())
    self.assertEquals(invoice.getDestinationDecision(), person.getRelativeUrl())
    self.assertTrue(invoice.getStartDate() >= before_date)
    self.assertTrue(invoice.getStartDate() <= after_date)
    self.assertEquals(invoice.getStartDate(), invoice.getStopDate())

  def test_do_nothing_if_invoice_is_ongoing(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    invoice = self.createInvoiceTransaction()
    self.portal.portal_workflow._jumpToStateFor(invoice, 'confirmed')
    contract.edit(
      destination_section_value=person,
      causality_value=invoice,
    )
    self.assertEquals(contract.getValidationState(), "invalidated")
    self.tic()

    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertEquals(contract2.getCausality(""), invoice.getRelativeUrl())
    self.assertEquals(contract2.getValidationState(), "invalidated")

  def test_forget_current_cancelled_invoice(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    invoice = self.createInvoiceTransaction()
    self.portal.portal_workflow._jumpToStateFor(invoice, 'cancelled')
    contract.edit(
      destination_section_value=person,
      causality_value=invoice,
    )
    self.assertEquals(contract.getValidationState(), "invalidated")
    self.tic()

    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertEquals(contract2.getCausality(""), "")
    self.assertEquals(contract2.getValidationState(), "invalidated")

  def test_forget_current_grouped_invoice(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    invoice = self.createInvoiceTransaction()
    line = invoice.newContent(
      portal_type="Sale Invoice Transaction Line",
      source="account_module/receivable", 
      grouping_reference="foo",
    )
    line.getSourceValue().getAccountType()
    self.portal.portal_workflow._jumpToStateFor(invoice, 'stopped')
    contract.edit(
      destination_section_value=person,
      causality_value=invoice,
    )
    self.assertEquals(contract.getValidationState(), "invalidated")
    self.tic()

    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertEquals(contract2.getCausality(""), "")
    self.assertEquals(contract2.getValidationState(), "invalidated")

  def test_do_nothing_if_invoice_is_not_grouped(self):
    person, instance, subscription = self.createNeededDocuments()
    contract = self.createCloudContract()
    invoice = self.createInvoiceTransaction()
    invoice.newContent(
      portal_type="Sale Invoice Transaction Line",
      source="account_module/receivable", 
    )
    self.portal.portal_workflow._jumpToStateFor(invoice, 'stopped')
    contract.edit(
      destination_section_value=person,
      causality_value=invoice,
    )
    self.assertEquals(contract.getValidationState(), "invalidated")
    self.tic()

    contract2 = instance.SoftwareInstance_requestValidationPayment()
    self.assertEquals(contract2.getRelativeUrl(), contract.getRelativeUrl())
    self.assertEquals(contract2.getCausality(""), invoice.getRelativeUrl())
    self.assertEquals(contract2.getValidationState(), "invalidated")

class TestSlapOSPerson_isAllowedToAllocate(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def createPerson(self):
    new_id = self.generateNewId()
    return self.portal.person_module.newContent(
      portal_type='Person',
      title="Person %s" % new_id,
      reference="TESTPERS-%s" % new_id,
      )

  def createCloudContract(self):
    new_id = self.generateNewId()
    return self.portal.cloud_contract_module.newContent(
      portal_type='Cloud Contract',
      title="Contract %s" % new_id,
      reference="TESTCONTRACT-%s" % new_id,
      )

  def test_not_allowed_by_default(self):
    person = self.createPerson()
    result = person.Person_isAllowedToAllocate()
    self.assertEquals(result, False)

  def test_allowed_if_has_a_validated_contract(self):
    person = self.createPerson()
    contract = self.createCloudContract()
    contract.edit(
      destination_section_value=person
    )
    self.portal.portal_workflow._jumpToStateFor(contract, 'validated')
    self.tic()
    result = person.Person_isAllowedToAllocate()
    self.assertEquals(result, True)

  def test_not_allowed_if_has_an_invalidated_contract(self):
    person = self.createPerson()
    contract = self.createCloudContract()
    contract.edit(
      destination_section_value=person
    )
    self.portal.portal_workflow._jumpToStateFor(contract, 'invalidated')
    self.tic()
    result = person.Person_isAllowedToAllocate()
    self.assertEquals(result, False)

  def test_not_allowed_if_no_related_contract(self):
    person = self.createPerson()
    contract = self.createCloudContract()
    self.portal.portal_workflow._jumpToStateFor(contract, 'validated')
    self.tic()
    result = person.Person_isAllowedToAllocate()
    self.assertEquals(result, False)
