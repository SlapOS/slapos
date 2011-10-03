from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random

class TestVifibSlapComputerPartitionUpdate(TestVifibSlapWebServiceMixin):
  def stepRequestSoftwareInstanceUpdate(self, sequence, **kw):
    self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid']).requestUpdateComputerPartition()

  def stepCheckComputerPartitionInstanceUpdateSalePackingListConfirmed(self,
      sequence, **kw):
    self._checkComputerPartitionSalePackingListState('confirmed',
        self.portal.portal_preferences.getPreferredInstanceUpdateResource(),
        sequence)

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
      RequestSoftwareInstanceUpdate
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionNoInstanceUpdateSalePackingList
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
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckActivityRequestInProgress(self, sequence, **kw):
    software_instance_uid = sequence['software_instance_uid']
    software_type = sequence.get('software_type', 'requested_reference')
    requested_partition_reference = sequence.get('software_type', 'requested_reference')
    tag = "%s_%s_%s_inProgress" % (software_instance_uid,
        software_type, requested_partition_reference)

    self.assertNotEqual(0, self.portal.portal_activities.
      countMessageWithTag(tag))

  def test_update_not_created_request_in_progress(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = self\
        .prepare_install_requested_computer_partition_sequence_string + """
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
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
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckActivityPersonRequestInProgress(self, sequence, **kw):
    person_uid = self.portal.ERP5Site_getAuthenticatedMemberPersonValue(
      'test_vifib_customer').getUid()
    software_type = sequence.get('software_type', 'RootSoftwareInstance')
    software_title = sequence['root_software_instance_title']
    tag = "%s_%s_%s_inProgress" % (person_uid, software_type,
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
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionUpdate))
  return suite
