computer = state_change['object']
context.REQUEST.set('computer_certificate', None)
context.REQUEST.set('computer_key', None)
destination_reference = computer.getDestinationReference()
if destination_reference is None:
  raise ValueError('No certificate')
context.getPortalObject().portal_certificate_authority.revokeCertificate(destination_reference)
computer.setDestinationReference(None)
