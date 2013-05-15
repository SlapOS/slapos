from AccessControl import ClassSecurityInfo, Unauthorized, getSecurityManager
from Products.ERP5.Document.Person import Person as ERP5Person
from Products.ERP5Type import Permissions

class Person(ERP5Person):
  security = ClassSecurityInfo()
  security.declarePublic('getCertificate')

  def _checkCertificateRequest(self):
    try:
      self.checkUserCanChangePassword()
    except Unauthorized:
      # in ERP5 user has no SetOwnPassword permission on Person document
      # referring himself, so implement "security" by checking that currently
      # logged in user is trying to get/revoke his own certificate
      reference = self.getReference()
      if not reference:
        raise
      if getSecurityManager().getUser().getId() != reference:
        raise

  def _getCertificate(self):
    return self.getPortalObject().portal_certificate_authority\
      .getNewCertificate(self.getReference())

  def _revokeCertificate(self):
    return self.getPortalObject().portal_certificate_authority\
      .revokeCertificateByCommonName(self.getReference())

  def getCertificate(self):
    """Returns new SSL certificate"""
    self._checkCertificateRequest()
    return self._getCertificate()

  security.declarePublic('revokeCertificate')
  def revokeCertificate(self):
    """Revokes existing certificate"""
    self._checkCertificateRequest()
    self._revokeCertificate()

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getTitle')
  def getTitle(self, **kw):
    """
      Returns the title if it exists or a combination of
      first name and last name
    """
    title = ERP5Person.getTitle(self, **kw)
    test_title = title.replace(' ', '')
    if test_title == '':
      return self.getDefaultEmailCoordinateText(test_title)
    else:
      return title
