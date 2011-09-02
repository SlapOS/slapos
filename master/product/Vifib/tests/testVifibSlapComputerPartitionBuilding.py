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

class TestVifibSlapComputerPartitionBuilding(TestVifibSlapWebServiceMixin):
  ########################################
  # ComputerPartition.building
  ########################################

  def test_ComputerPartition_building_afterRegister(self):
    """
    Check that calling ComputerPartition.building after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      CheckNotFoundComputerPartitionBuildingAfterRegisterCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_building_success(self):
    """
    Check that calling ComputerPartition.building change the sale packing
    list state to started.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_ComputerPartition_building_alreadyConfirmedSalePackingList(self):
    """
    Check that calling ComputerPartition.building failed if there is already
    confirmed sale packing list
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_building_computer_partition_sequence_string + """
      SlapLoginCurrentComputer
      SoftwareInstanceBuilding
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListStarted
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionBuilding))
  return suite
