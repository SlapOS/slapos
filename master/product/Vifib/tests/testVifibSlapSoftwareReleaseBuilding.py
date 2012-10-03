from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapSoftwareReleaseBuilding(TestVifibSlapWebServiceMixin):
  ########################################
  # SoftwareRelease.building
  ########################################

  def test_SoftwareRelease_building_afterRegister(self):
    """
    Check that calling SoftwareRelease.building after just registration raises a
    NotFoundError
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SelectNewSoftwareReleaseUri \
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseBuildingAfterRegisterCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSoftwareReleaseBuilding))
  return suite
