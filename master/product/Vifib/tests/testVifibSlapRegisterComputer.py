from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapRegisterComputer(TestVifibSlapWebServiceMixin):

  ########################################
  # slap.registerComputer
  ########################################

  def test_slap_registerComputer_unknowComputerUid(self):
    """
    Check the slap.registerComputer without any Computer document
    does not fail
    """
    sequence_list = SequenceList()
    sequence_string = '\
      SetRandomComputerReference \
      LoginDefaultUser \
      CheckSuccessSlapRegisterComputerCall \
      Logout \
      Tic \
      LoginDefaultUser \
      CheckUnexistingComputer \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputer_draftComputer(self):
    """
    Check the slap.registerComputer does not fail if
    a draft computer exits.
    """
    sequence_list = SequenceList()
    # Note: ERP5TypeTestCase is used as login to being able to test it
    sequence_string = '\
      LoginTestVifibAdmin \
      CreateDraftComputer \
      Tic \
      Logout \
      \
      LoginDefaultUser \
      CheckSuccessSlapRegisterComputerCall \
      Logout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputer_validatedComputer(self):
    """
    Check the slap.registerComputer does not fail if
    a validated computer exists.
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CustomerRegisterNewComputer \
      Tic \
      SetComputerCoordinatesFromComputerTitle \
      ComputerSetAllocationScopeOpenPublic \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer\
      CheckSuccessSlapRegisterComputerCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerComputer_TwoValidatedComputer(self):
    """
    Check the slap.registerComputer works in case of more then one computer available
    """
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      CustomerRegisterNewComputer \
      Tic \
      SetComputerCoordinatesFromComputerTitle \
      ComputerSetAllocationScopeOpenPublic \
      Tic \
      Logout \
      \
      LoginTestVifibAdmin \
      CustomerRegisterNewComputer \
      Tic \
      SetComputerCoordinatesFromComputerTitle \
      ComputerSetAllocationScopeOpenPublic \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer\
      CheckSuccessSlapRegisterComputerCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapRegisterComputer))
  return suite
