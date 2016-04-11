computer = context
try:
  computer.revokeCertificate()
  message = context.Base_translateString('Certificate revoked.')
except ValueError:
  message = context.Base_translateString('No certificate found.')

return context.Base_redirect(keep_items=dict(portal_status_message=message))
