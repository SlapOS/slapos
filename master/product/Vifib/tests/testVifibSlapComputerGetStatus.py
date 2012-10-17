from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.tests.backportUnittest import skip
import transaction
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from slapos import slap

class TestVifibSlapComputerGetStatus(TestVifibSlapWebServiceMixin):
  ########################################
  # Computer.getStatus
  ########################################

  def stepCheckNoDataComputerGetStatusCall(self, sequence, **kw):
    """
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(
        computer_guid)

    status = computer.getStatus()
    self.assertEquals('SlapOS Master', status['user'])
    self.assertEquals('#error no data found for %s' % \
        sequence["computer_reference"], status['text'])

  def test_Computer_getStatus_noComputer(self):
    """
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckNoDataComputerGetStatusCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckOKComputerGetStatusCall(self, sequence, **kw):
    """
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(
        computer_guid)

    status = computer.getStatus()
    self.assertEquals(sequence['computer_reference'], status['user'])
    self.assertEquals('#access %s' % sequence["computer_reference"], 
                      status['text'])

  def test_Computer_OK_getStatus(self):
    """
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_computer + '\
      SlapLoginCurrentComputer \
      CheckSuccessComputerGetComputerPartitionCall \
      CheckOKComputerGetStatusCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckErrorComputerGetStatusCall(self, sequence, **kw):
    """
    """
    computer_guid = sequence["computer_reference"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    computer = self.slap.registerComputer(
        computer_guid)

    status = computer.getStatus()
    self.assertEquals(sequence['computer_reference'], status['user'])
    self.assertEquals('#error bang', status['text'])

  def stepSoftwareReleaseError(self, sequence,
      **kw):
    """
    """
    url = sequence["software_release_uri"]
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    software_release = self.slap.registerSoftwareRelease(url)

    software_release.error("ErrorLog")

  def stepComputerBang(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    slap_computer = self.slap.registerComputer(
      sequence['computer_reference'])
    slap_computer.bang('foo')

  def test_Computer_Error_getStatus(self):
    """
    """
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + '\
      SlapLoginCurrentComputer \
      ComputerBang \
      CheckErrorComputerGetStatusCall \
      SlapLogout \
      LoginERP5TypeTestCase \
      CheckSiteConsistency \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerGetStatus))
  return suite
