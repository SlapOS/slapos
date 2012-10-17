from Products.ERP5Type.tests.Sequence import SequenceList
import transaction
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapComputer(TestVifibSlapWebServiceMixin):
  def stepCheckRequestedComputerCertificate(self, sequence, **kw):
    computer = sequence['requested_computer']
    sequence['computer_reference'] = computer._computer_id
    certificate_dict = computer.generateCertificate()
    transaction.commit()
    self.assertTrue('certificate' in certificate_dict)
    self.assertTrue('key' in certificate_dict)
    self.assertNotEqual(None, certificate_dict['certificate'])
    self.assertNotEqual(None, certificate_dict['key'])
    self.assertTrue(certificate_dict['key'].startswith(
      '-----BEGIN PRIVATE KEY-----'))
    self.assertTrue('-----BEGIN CERTIFICATE-----' in \
      certificate_dict['certificate'])
    computer = self.portal.portal_catalog.getResultValue(
      reference=sequence['computer_reference'], portal_type='Computer')
    self.assertNotEqual(None, computer.getDestinationReference())
    sequence['certificate_reference'] = computer.getDestinationReference()

  def test_request(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginTestVifibAdmin \
      SetComputerTitle \
      RequestComputer \
      CleanTic \
      CheckRequestedComputerCertificate \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckDoubleRequestRaisesNotImplementedError(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    person.requestComputer(computer_title=sequence['computer_title'])
    transaction.commit()
    self.assertRaises(NotImplementedError, person.requestComputer,
      computer_title=sequence['computer_title'])

  def test_request_twice_activity(self):
    sequence_list = SequenceList()
    sequence_string = '\
      LoginTestVifibAdmin \
      SetComputerTitle \
      CheckDoubleRequestRaisesNotImplementedError \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckComputerNoCertificate(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      reference=sequence['computer_reference'], portal_type='Computer')
    self.assertEqual(None, computer.getDestinationReference())

  def test_revokeCertificate(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginTestVifibAdmin \
      SetComputerTitle \
      RequestComputer \
      CleanTic \
      CheckRequestedComputerCertificate \
      RevokeComputerCertificate \
      CheckComputerNoCertificate \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckRevokeComputerCertificateRaisesValueError(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      reference=sequence['computer_reference'], portal_type='Computer')
    self.assertRaises(ValueError, computer.revokeCertificate)

  def test_revokeCertificateRevoked(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginTestVifibAdmin \
      SetComputerTitle \
      RequestComputer \
      CleanTic \
      CheckRequestedComputerCertificate \
      RevokeComputerCertificate \
      CheckComputerNoCertificate \
      SlapLogout \
      LoginTestVifibAdmin \
      CheckRevokeComputerCertificateRaisesValueError \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_getCertificate(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginTestVifibAdmin \
      SetComputerTitle \
      RequestComputer \
      CleanTic \
      CheckRequestedComputerCertificate \
      RevokeComputerCertificate \
      CheckComputerNoCertificate \
      CleanTic \
      CheckRequestedComputerCertificate \
      SlapLogout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepCheckGetComputerCertificateRaisesValueError(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      reference=sequence['computer_reference'], portal_type='Computer')
    self.assertRaises(ValueError, computer.generateCertificate)

  def test_getCertificateNotRevoked(self):
    sequence_list = SequenceList()
    sequence_string = '\
      SlapLoginTestVifibAdmin \
      SetComputerTitle \
      RequestComputer \
      CleanTic \
      CheckRequestedComputerCertificate \
      SlapLogout \
      LoginTestVifibAdmin \
      CheckGetComputerCertificateRaisesValueError \
      Logout \
    '
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputer))
  return suite
