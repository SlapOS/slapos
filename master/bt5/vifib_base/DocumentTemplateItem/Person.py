from AccessControl import ClassSecurityInfo
from Products.ERP5.Document.Person import Person as ERP5Person
class Person(ERP5Person):
  security = ClassSecurityInfo()
  security.declarePublic('getCertificate')

  def _checkReference(self):
    if not self.getReference():
      raise ValueError('No reference set.')

  def _getCertificate(self):
    return self.getPortalObject().portal_certificate_authority\
      .getNewCertificate(self.getReference())

  def _revokeCertificate(self):
    return self.getPortalObject().portal_certificate_authority\
      .revokeCertificateByCommonName(self.getReference())

  def getCertificate(self):
    """Returns new SSL certificate"""
    self._checkReference()
    self.checkUserCanChangePassword()
    return self._getCertificate()

  security.declarePublic('revokeCertificate')
  def revokeCertificate(self):
    """Revokes existing certificate"""
    self._checkReference()
    self.checkUserCanChangePassword()
    self._revokeCertificate()
