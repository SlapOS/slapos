computer = context
request = context.REQUEST
try:
  computer.generateCertificate()
  request.set('portal_status_message', context.Base_translateString('Certificate created.'))
except ValueError:
  request.set('portal_status_message', context.Base_translateString('Certificate is still active, please revoke existing one.'))
request.set('your_certificate', request.get('computer_certificate'))
request.set('your_key', request.get('computer_key'))

return context.Computer_viewConnectionInformationAsWeb()
