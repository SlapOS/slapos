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

class TestVifibSlapRegisterSoftwareRelease(TestVifibSlapWebServiceMixin):
  ########################################
  # slap.registerSoftwareRelease
  ########################################

  def test_slap_registerSoftwareRelease_validatedSoftwareRelease(self):
    """
    Check the slap.registerSoftwareRelease does not fail if
    a validated computer exists.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      LoginTestVifibAdmin \
      CreateComputer \
      Tic \
      Logout \
      \
      LoginTestVifibDeveloper \
      SelectNewSoftwareReleaseUri \
      CreateSoftwareRelease \
      Tic \
      SubmitSoftwareRelease \
      Tic \
      CreateSoftwareProduct \
      Tic \
      ValidateSoftwareProduct \
      Tic \
      SetSoftwareProductToSoftwareRelease \
      PublishByActionSoftwareRelease \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerSoftwareRelease_unknowSoftwareReleaseUid(self):
    """
    Check the slap.registerSoftwareRelease without any SoftwareRelease document
    does not fail
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SelectNewSoftwareReleaseUri \
      \
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerSoftwareRelease_draftSoftwareRelease(self):
    """
    Check the slap.registerSoftwareRelease does not fail if
    a draft computer exits.
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      LoginTestVifibDeveloper \
      SelectNewSoftwareReleaseUri \
      CreateSoftwareRelease \
      Tic \
      \
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_slap_registerSoftwareRelease_TwoValidatedSoftwareRelease(self):
    """
    Check the slap.registerSoftwareRelease works
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      LoginTestVifibDeveloper \
      SelectNewSoftwareReleaseUri \
      CreateSoftwareRelease \
      Tic \
      SubmitSoftwareRelease \
      Tic \
      CreateSoftwareProduct \
      Tic \
      ValidateSoftwareProduct \
      Tic \
      SetSoftwareProductToSoftwareRelease \
      PublishByActionSoftwareRelease \
      Logout \
      \
      LoginTestVifibDeveloper \
      SelectNewSoftwareReleaseUri \
      CreateSoftwareRelease \
      Tic \
      SubmitSoftwareRelease \
      Tic \
      CreateSoftwareProduct \
      Tic \
      ValidateSoftwareProduct \
      Tic \
      SetSoftwareProductToSoftwareRelease \
      PublishByActionSoftwareRelease \
      Logout \
      \
      SlapLoginCurrentComputer \
      CheckSuccessSlapRegisterSoftwareReleaseCall \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapRegisterSoftwareRelease))
  return suite
