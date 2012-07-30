from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from random import random
from Products.ERP5Type.tests.backportUnittest import skip
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod

class TestVifibSlapComputerPartitionUpdate(TestVifibSlapWebServiceMixin):
  def stepRequestSoftwareInstanceUpdate(self, sequence, **kw):
    instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    method_dict = {
        'start_requested': instance.requestStart,
        'stop_requested': instance.requestStop,
        'destroy_requested': instance.requestDestroy,
        }
    method_dict[instance.getSlapState()](
        software_release=instance.getRootSoftwareReleaseUrl(),
        instance_xml='<?xml version="1.0" ' \
                     'encoding="utf-8"?><instance><parameter id="foo">bar</parameter></instance>',
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

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
      CallConfirmOrderedSaleOrderAlarm
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceBuilding
      Tic
      SlapLogout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout
      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout

      # prepared initally stopped instance

      SlapLoginCurrentComputer
      CheckSuccessComputerGetComputerPartitionCall
      SlapLogout

      LoginTestVifibCustomer
      RequestSoftwareInstanceUpdate
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
      CheckComputerPartitionInstanceSetupSalePackingListDelivered
      CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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

  def test_update_support_started_instance_hosting(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string \
      + """
        SlapLoginCurrentComputer
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckSuccessComputerGetComputerPartitionCall
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
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckComputerPartitionInstanceHostingSalePackingListStopped
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckSuccessComputerGetComputerPartitionCall
        SlapLogout

        LoginTestVifibCustomer
        RequestSoftwareInstanceUpdate
        Tic
        Logout

        LoginDefaultUser
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckComputerPartitionInstanceHostingSalePackingListStopped
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
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
        CheckComputerPartitionInstanceUpdateSalePackingListDelivered
        Logout

        LoginERP5TypeTestCase
        CheckSiteConsistency
        Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('Update is forbidden on destroyed instance')
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

  @skip('Update is forbidden on destroyed instance')
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
    if instance.getPortalType() == "Software Instance":
      shared = False
    elif instance.getPortalType() == "Slave Instance":
      shared = True
    else:
      raise NotImplementedError
    method_dict = {
        'start_requested': instance.requestStart,
        'stop_requested': instance.requestStop,
        'destroy_requested': instance.requestDestroy,
        }
    self.assertRaises(UnsupportedWorkflowMethod, 
        method_dict[instance.getSlapState()],
        software_release=instance.getRootSoftwareReleaseUrl(),
        instance_xml=instance.getTextContent(),
        software_type=instance.getSourceReference(),
        sla_xml=instance.getSlaXml(),
        shared=shared,
        )

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
      software_type="RootSoftwareInstance",
      instance_xml=self.minimal_correct_xml,
      sla_xml="",
      shared=False,
      state="started")
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

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionUpdate))
  return suite
