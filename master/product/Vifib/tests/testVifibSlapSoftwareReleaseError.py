from Products.ERP5Type.tests.Sequence import SequenceList
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
      CheckNameErrorSoftwareReleaseErrorAfterRegisterCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSoftwareReleaseError))
  return suite
