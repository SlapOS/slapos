person = context.ERP5Site_getAuthenticatedMemberPersonValue()
try:
  person.revokeCertificate()
  message = context.Base_translateString('Certificate revoked.')
except ValueError:
  message = context.Base_translateString('No certificate found.')

return context.getWebSiteValue().myspace.my_account.Base_redirect(keep_items=dict(portal_status_message=message))
