from DateTime import DateTime
from AccessControl.SecurityManagement import newSecurityManager
from Products.ERP5Type.Errors import UnsupportedWorkflowMethod
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import expectedFailure
from Products.ERP5Type.tests.backportUnittest import skip
from Products.ERP5Type.tests.SecurityTestCase import AssertNoPermissionMethod, \
    AssertPermissionMethod
from Products.ERP5Type import Permissions
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from VifibMixin import testVifibMixin
from random import random
from slapos import slap
import urllib
import urlparse
import httplib
from xml_marshaller import xml_marshaller
import transaction
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapSoftwareReleaseError(TestVifibSlapWebServiceMixin):
  ########################################
  # SoftwareRelease.error
  ########################################

  def test_SoftwareRelease_error_afterRegister(self):
    """
    Check that calling SoftwareRelease.error after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      SelectNewSoftwareReleaseUri \
      CheckNotFoundSoftwareReleaseErrorAfterRegisterCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_error_SetupResource_ConfirmedState(self):
    """
    Check that calling SoftwareRelease.error works in 
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListErrorText \
      CheckConfirmedPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_error_SetupResource_CancelledState(self):
    """
    Check that calling SoftwareRelease.error works in 
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListNoErrorText \
      CheckCancelledPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_error_SetupResource_StartedState(self):
    """
    Check that calling SoftwareRelease.error works in 
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListErrorText \
      CheckStartedPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_error_SetupResource_StoppedState(self):
    """
    Check that calling SoftwareRelease.error works in 
    stopped state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      StopPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListNoErrorText \
      CheckStoppedPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_error_SetupResource_DeliveredState(self):
    """
    Check that calling SoftwareRelease.error works in 
    delivered state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      StopPurchasePackingList \
      DeliverPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListNoErrorText \
      CheckDeliveredPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_error_twoPurchasePackingList(self):
    """
    Check that calling SoftwareRelease.error uses the latest purchase packing
    list for calculation
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_two_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginDefaultUser \
      StepPurchasePackingListBStartDateAfterPurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListErrorText \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_string = self.prepare_two_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginDefaultUser \
      StepPurchasePackingListBStartDateBeforePurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseErrorCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckPurchasePackingListErrorText \
      Logout \
      '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSoftwareReleaseError))
  return suite
