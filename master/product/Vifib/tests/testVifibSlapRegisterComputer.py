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
      CreateComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer\
      CheckSuccessSlapRegisterComputerCall \
      SlapLogout \
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
      CreateComputer \
      Tic \
      Logout \
      \
      LoginTestVifibAdmin \
      CreateComputer \
      Tic \
      Logout \
      \
      SlapLoginCurrentComputer\
      CheckSuccessSlapRegisterComputerCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapRegisterComputer))
  return suite
