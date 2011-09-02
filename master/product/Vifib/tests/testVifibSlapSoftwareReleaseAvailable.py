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

class TestVifibSlapSoftwareReleaseAvailable(TestVifibSlapWebServiceMixin):
  ########################################
  # SoftwareRelease.available
  ########################################

  def test_SoftwareRelease_available_afterRegister(self):
    """
    Check that calling SoftwareRelease.available after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      SelectNewSoftwareReleaseUri \
      CheckNotFoundSoftwareReleaseAvailableAfterRegisterCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_available_SetupResource_ConfirmedState(self):
    """
    Check that calling SoftwareRelease.available works in 
    confirmed state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_available_SetupResource_CancelledState(self):
    """
    Check that calling SoftwareRelease.available works in 
    cancelled state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      CancelPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckCancelledPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_available_SetupResource_StartedState(self):
    """
    Check that calling SoftwareRelease.available works in 
    started state with the setup resource
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      LoginDefaultUser \
      StartPurchasePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_available_SetupResource_StoppedState(self):
    """
    Check that calling SoftwareRelease.available works in 
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
      CheckNotFoundSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_available_SetupResource_DeliveredState(self):
    """
    Check that calling SoftwareRelease.available works in 
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
      CheckNotFoundSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckDeliveredPurchasePackingList \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_available_twoPurchasePackingList(self):
    """
    Check that calling SoftwareRelease.available uses the latest purchase packing
    list for calculation
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_two_purchase_packing_list + '\
      LoginDefaultUser \
      StepPurchasePackingListBStartDateAfterPurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingListB \
      Logout'
    sequence_list.addSequenceString(sequence_string)
    sequence_string = self.prepare_two_purchase_packing_list + '\
      LoginDefaultUser \
      StepPurchasePackingListBStartDateBeforePurchasePackingListA \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessSoftwareReleaseAvailableCall \
      Tic \
      SlapLogout \
      LoginDefaultUser \
      CheckStoppedPurchasePackingListB \
      Logout'
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSoftwareReleaseAvailable))
  return suite
