computer = state_change['object']

if computer.getDestinationReference() is not None:
  context.REQUEST.set("computer_certificate", None)
  context.REQUEST.set("computer_key", None)
  raise ValueError('Certificate still active.')

ca = context.getPortalObject().portal_certificate_authority
certificate_dict = ca.getNewCertificate(computer.getReference())

computer.setDestinationReference(certificate_dict["id"])

context.REQUEST.set("computer_certificate", certificate_dict["certificate"])
context.REQUEST.set("computer_key", certificate_dict["key"])
