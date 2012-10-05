from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapSoftwareReleaseDestroyed(TestVifibSlapWebServiceMixin):
  ########################################
  # SoftwareRelease.destroyed
  ########################################

  def test_SoftwareRelease_destroyed_afterRegister(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      SelectNewSoftwareReleaseUri \
      CheckNameErrorSoftwareReleaseDestroyedAfterRegisterCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_SoftwareRelease_destroyed_SetupResource_ConfirmedState(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_software_release_purchase_packing_list + '\
      SlapLoginCurrentComputer \
      CheckNotFoundSoftwareReleaseDestroyedCall \
      Tic \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSoftwareReleaseUnavailableForRequest \
      CheckSoftwareReleaseNotInPublicTable \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSoftwareReleaseDestroyed))
  return suite
