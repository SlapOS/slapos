from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random
from slapos import slap

class TestVifibSlapComputerPartitionUpdate(TestVifibSlapWebServiceMixin):
  def stepRequestSoftwareInstanceUpdate(self, sequence, **kw):
    self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestUpdateComputerPartition()

  def stepCheckComputerPartitionInstanceUpdateSalePackingListDelivered(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('delivered',
        self.portal.portal_preferences.getPreferredInstanceUpdateResource(),
        sequence)

  def stepPersonRequestStoppedSoftwareInstance(self, sequence, **kw):
    self.stepPersonRequestSoftwareInstance(sequence, state='stopped')

  def stepCheckComputerPartitionNoInstanceUpdateSalePackingList(self,
      sequence, **kw):
    self._checkComputerPartitionNoSalePackingList(
        self.portal.portal_preferences.getPreferredInstanceUpdateResource(),
        sequence)

  # expected scenarios
  def test_update_support_stopped_instance_setup(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestStoppedSoftwareInstance
      Tic
      Logout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceBuilding
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStarted
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout

      # prepared initally stopped instance

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout

      LoginTestVifibCustomer
      RequestSoftwareInstanceUpdate
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      SlapLoginCurrentComputer
      CheckStoppedComputerPartitionGetStateCall
      SlapLogout

      SlapLoginCurrentComputer
      SoftwareInstanceStopped
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceHostingSalePackingList
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionInstanceUpdateSalePackingListDelivered
      Logout

      SlapLoginCurrentComputer
      CheckEmptyComputerGetComputerPartitionCall
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_support_started_instance_hosting(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string \
      + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        Logout

        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        SlapLoginCurrentComputer
        CheckStartedComputerPartitionGetStateCall
        SlapLogout

        SlapLoginCurrentComputer
        SoftwareInstanceStarted
        Tic
        SlapLogout

        LoginDefaultUser
        CheckComputerPartitionInstanceHostingSalePackingListStarted
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
        Logout

        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_support_delivered_instance_hosting(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_stopped_computer_partition_sequence_string \
      + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        Logout

        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        SlapLoginCurrentComputer
        CheckStoppedComputerPartitionGetStateCall
        SlapLogout

        SlapLoginCurrentComputer
        SoftwareInstanceStopped
        Tic
        SlapLogout

        LoginDefaultUser
        CheckComputerPartitionInstanceHostingSalePackingListDelivered
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
        Logout

        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckUpdateSalePackingListErrorText(self, sequence, **kw):
    """
    Check that the sale packing list has an error log
    """
    computer_partition = self.portal.portal_catalog.getResultValue(
        uid=sequence['computer_partition_uid'])
    packing_list_line = [q for q in computer_partition
        .getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)
        if q.getResource() == \
          self.portal.portal_preferences.getPreferredInstanceUpdateResource()][0]
    packing_list = packing_list_line.getParentValue()
    self.assertFalse(packing_list.getComment('').endswith("ErrorLog"))

  def test_update_support_error(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_stopped_computer_partition_sequence_string \
      + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        Logout

        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        SlapLoginCurrentComputer
        CheckStoppedComputerPartitionGetStateCall
        SlapLogout

        SlapLoginCurrentComputer
        CheckSuccessComputerPartitionErrorCall
        Tic
        SlapLogout

        LoginDefaultUser
        CheckComputerPartitionInstanceHostingSalePackingListDelivered
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        CheckUpdateSalePackingListErrorText
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # ignored scenarios
  def test_update_not_created_confirmed_instance_setup(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_install_requested_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_not_created_started_instance_setup(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_building_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_not_created_delivered_instance_setup(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestStoppedSoftwareInstance
      Tic
      Logout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceBuilding
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStarted
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout


      LoginDefaultUser
      DeliverSalePackingList
      Tic
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      Logout

      # prepared delivered instance setup delivery

      LoginTestVifibCustomer
      RequestSoftwareInstanceUpdateRaisesValidationFailed
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_not_created_confirmed_instance_hosting(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_installed_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_not_created_stopped_instance_hosting(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_stop_requested_computer_partition_sequence_string + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_not_created_confirmed_instance_cleanup(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_destroy_requested_computer_partition + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_not_created_started_instance_cleanup(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_destroy_requested_computer_partition + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepRequestSoftwareInstanceUpdateRaisesValidationFailed(self, sequence,
    **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertRaises(ValidationFailed, instance.requestUpdateComputerPartition)

  def test_update_not_possible_delivered_instance_cleanup(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_destroyed_computer_partition + """
        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdateRaisesValidationFailed
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # low level activity locks
  def stepCheckActivityStartInProgress(self, sequence, **kw):
    self.assertNotEqual(0, self.portal.portal_activities.
      countMessageWithTag('%s_startInProgress' % sequence[
        'software_instance_uid']))

  def test_update_not_created_start_in_progress(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_stopped_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceStart
      Logout

      LoginDefaultUser
      CheckActivityStartInProgress
      Logout

      LoginTestVifibCustomer
      RequestSoftwareInstanceUpdate
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckActivityDestroyInProgress(self, sequence, **kw):
    self.assertNotEqual(0, self.portal.portal_activities.
      countMessageWithTag('%s_destroyInProgress' % sequence[
        'software_instance_uid']))

  def test_update_not_created_destruction_in_progress(self):
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_installed_computer_partition_sequence_string + """
      LoginTestVifibCustomer
      RequestSoftwareInstanceDestroy
      Logout

      LoginDefaultUser
      CheckActivityDestroyInProgress
      Logout

      LoginTestVifibCustomer
      RequestSoftwareInstanceUpdate
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepRequestComputerPartitionNoTic(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer_partition = self.slap.registerComputerPartition(
        sequence['computer_reference'],
        sequence['computer_partition_reference'])
    kw = dict(software_release=sequence['software_release_uri'],
      software_type=sequence.get('requested_software_type',
                                 'requested_software_type'),
      partition_reference=sequence.get('requested_reference',
        'requested_reference'),
      partition_parameter_kw=sequence.get('requested_parameter_dict', {}),
      filter_kw=sequence.get('requested_filter_dict', {}),
      state=sequence.get('instance_state'))

    slap_computer_partition.request(**kw)

  def stepCheckActivityRequestInProgress(self, sequence, **kw):
    hosting_subscription_uid = sequence['hosting_subscription_uid']
    requested_partition_reference = sequence.get('software_type', 'requested_reference')
    tag = "%s_%s_inProgress" % (hosting_subscription_uid,
        requested_partition_reference)

    self.assertNotEqual(0, self.portal.portal_activities.
      countMessageWithTag(tag))

  def test_update_not_created_request_in_progress(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_install_requested_computer_partition_sequence_string + """
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNoTic
      SlapLogout

      LoginDefaultUser
      CheckActivityRequestInProgress
      Logout

      LoginTestVifibCustomer
      RequestSoftwareInstanceUpdate
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckActivityPersonRequestInProgress(self, sequence, **kw):
    person_uid = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_customer').getUid()
    software_title = sequence['root_software_instance_title']
    tag = "%s_%s_inProgress" % (person_uid,
                                   software_title)

    self.assertNotEqual(0, self.portal.portal_activities.
      countMessageWithTag(tag))

  def stepPersonRequestSoftwareInstanceNoTic(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    software_release = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_release_uid'])
    software_title = self.id() + str(random())
    person.requestSoftwareInstance(
      software_release=software_release.getUrlString(),
      software_title=software_title,
      instance_xml=self.minimal_correct_xml,
      **kw)
    sequence.edit(root_software_instance_title=software_title)

  def test_update_not_created_person_request_in_progress(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_published_software_release + \
      self.prepare_formated_computer + """
      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestSoftwareInstanceNoTic
      Logout

      LoginDefaultUser
      CheckActivityPersonRequestInProgress
      Logout

      # and this that test finishes
      # it is proven that person data are begin in progress
      # but there is no way to request software instance update as...
      # ...it does not exists yet

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  # update triggers
  def stepSoftwareInstanceEditTitle(self, sequence,
    **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    instance.edit(
      title = instance.getTitle() + 'edited'
    )

  def stepSoftwareInstanceEditSourceReference(self, sequence,
    **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    instance.edit(
      source_reference = instance.getSourceReference() + 'edited'
    )

  def stepSoftwareInstanceEditTextContent(self, sequence,
    **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    text_content = instance.getTextContent()
    modified_xml = """<?xml version="1.0" encoding="utf-8"?>
      <instance><parameter id="ignore">value</parameter></instance>"""
    self.assertNotEqual(modified_xml, text_content)
    instance.edit(
      text_content = modified_xml
    )

  def stepSoftwareInstanceEditConnectionXml(self, sequence,
    **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    connection_xml = instance.getConnectionXml()
    self.assertNotEqual(connection_xml, self.minimal_correct_xml)
    instance.edit(
      connection_xml = self.minimal_correct_xml
    )

  def test_update_on_title_change(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_started_computer_partition_sequence_string + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        SoftwareInstanceEditTitle
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        Logout

        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout


        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_on_source_reference_change(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_started_computer_partition_sequence_string + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        SoftwareInstanceEditSourceReference
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        Logout

        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_update_on_text_content_change(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_started_computer_partition_sequence_string + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        SoftwareInstanceEditTextContent
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListConfirmed
        Logout

        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_no_update_on_connection_xml_change(self):
    sequence_list = SequenceList()
    sequence_string = \
      self.prepare_started_computer_partition_sequence_string + """
        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        SoftwareInstanceEditConnectionXml
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionNoInstanceUpdateSalePackingList
        Logout

        SlapLoginCurrentComputer
        CheckEmptyComputerGetComputerPartitionCall
        SlapLogout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionUpdate))
  return suite
