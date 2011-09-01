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

class TestVifibSlapComputerPartitionAvailable(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.available
  ########################################

  def test_ComputerPartition_available_afterRegister(self):
    """
    Check that calling ComputerPartition.available after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + """
      SlapLoginCurrentComputer
      CheckNotFoundComputerPartitionAvailableAfterRegisterCall
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_available_successConfirmed(self):
    """
    Check that calling ComputerPartition.available change the sale packing
    list state to stopped.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_installed_computer_partition_sequence_string
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_available_alreadyStartedSalePackingList(self):
    """
    Check that calling ComputerPartition.available more then once can be called
    without error and changes nothing
    """
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_installed_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionAvailable))
  return suite
