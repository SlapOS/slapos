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

class TestVifibSlapComputerPartitionGetSoftwareRelease(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.getSoftwareRelease
  ########################################

  def test_ComputerPartition_getSoftwareRelease_afterRegister(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease after just 
    registration raises a NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckNotFoundComputerPartitionGetSoftwareReleaseAfterRegisterCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_confirmedState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    confirmed state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_cancelledState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    cancelled state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_install_requested_computer_partition_sequence_string + '\
      LoginDefaultUser \
      SelectCurrentlyUsedSalePackingListUid \
      CancelSalePackingList \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_startedState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    started state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_stoppedState(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease works in 
    stopped state
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_getSoftwareRelease_twoSalePackingList(self):
    """
    Check that calling ComputerPartition.getSoftwareRelease    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_started_computer_partition_sequence_string + '\
      LoginDefaultUser \
      CheckPackingListAmountTwoComputerPartition \
      SetHostingAfterSetupStartDate \
      Tic \
      Logout \
      SlapLoginCurrentComputer \
      CheckSuccessComputerPartitionGetSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionGetSoftwareRelease))
  return suite
