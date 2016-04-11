person = context.ERP5Site_getAuthenticatedMemberPersonValue()
request = context.REQUEST
response = request.RESPONSE

if person is None:
  response.setStatus(403)
else:
  try:
    certificate = person.getCertificate()
    request.set('portal_status_message', context.Base_translateString('Certificate created.'))
  except ValueError:
    certificate = {'certificate': '', 'key': ''}
    request.set('portal_status_message', context.Base_translateString('Certificate was already requested, please revoke existing one.'))
    response.setStatus(403)
  request.set('your_certificate', certificate['certificate'])
  request.set('your_key', certificate['key'])

  return context.WebSection_viewCertificateAsWeb()
