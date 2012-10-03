from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip
import transaction
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputerGetSoftwareReleaseList(TestVifibSlapWebServiceMixin):
  ########################################
  # Computer.getSoftwareReleaseList
  ########################################

  @skip('ERP5/Zope does not follow REST API beacuse it is not possible to '
    'configure  Cookie Crumbler to ignore portal_slap')
  def test_Computer_getSoftwareReleaseList_unknowComputerUid(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginRandomComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
      CheckUnexistingComputer \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('ERP5/Zope does not follow REST API beacuse it is not possible to '
    'configure  Cookie Crumbler to ignore portal_slap')
  def test_Computer_getSoftwareReleaseList_draftComputer(self):
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      Tic \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_validatedComputer(self):
    """
    Check that getSoftwareReleaseList returns an empty result if the
    validated computer is not related to any packing list.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_Computer_getSoftwareReleaseList_validatedAndDraftComputer(self):
    """
    Check that getSoftwareReleaseList returns an empty result if there are
    one draft and one validated computer.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout '\
      + self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckEmptyComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @skip('ERP5/Zope does not follow REST API beacuse it is not possible to '
    'configure  Cookie Crumbler to ignore portal_slap')
  def test_Computer_getSoftwareReleaseList_TwoValidatedComputer(self):
    # XXX: It shall be part of VifibMachineAuthentication test suite
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      LoginDefaultUser \
      DuplicateAndValidateCurrentComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckUnauthorizedComputerGetSoftwareReleaseListCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    try:
      sequence_list.play(self)
    finally:
      self.login('ERP5TypeTestCase')
      for c in self.portal.computer_module.contentValues():
        if c.getValidationState() == 'validated':
          c.invalidate()
          transaction.commit()

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerGetSoftwareReleaseList))
  return suite
