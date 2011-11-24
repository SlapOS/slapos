from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

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
      CustomerRegisterNewComputer
      Tic
      SetComputerCoordinatesFromComputerTitle
      ComputerSetAllocationScopeOpenPublic
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
