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

class TestVifibSlapComputerPartitionConnection(TestVifibSlapWebServiceMixin):

  ########################################
  # ComputerPartition.getConnectionParameter
  # ComputerPartition.setConnectionDict
  ########################################

  def test_ComputerPartition_Connection(self):
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibDeveloper
      SelectNewSoftwareReleaseUri
      CreateSoftwareRelease
      Tic
      SubmitSoftwareRelease
      Tic
      CreateSoftwareProduct
      Tic
      ValidateSoftwareProduct
      Tic
      SetSoftwareProductToSoftwareRelease
      PublishByActionSoftwareRelease
      Logout

      LoginTestVifibAdmin
      CreateComputer
      Tic
      Logout

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginTestVifibAdmin
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckGetSetConnectionDict
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionConnection))
  return suite
