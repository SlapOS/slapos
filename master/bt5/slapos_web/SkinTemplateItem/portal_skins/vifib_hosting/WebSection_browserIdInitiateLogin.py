def loginFailed():
  context.getWebSiteValue().login_form.Base_redirect(keep_items={'portal_status_message': 'Login with Browser ID failed.'})
assertion = context.REQUEST.get('assertion')
data = context.BrowserID_validateAssertion(assertion)

if data is None:
  return loginFailed()

if data.get('status', 'failure') != 'okay':
  return loginFailed()

login = data.get('email', '').encode('utf-8')

if login == '':
  return loginFailed()

hash = context.Base_getHMAC(assertion, assertion)
context.REQUEST.RESPONSE.setCookie('__ac_browser_id_hash', hash, path='/')
context.BrowserID_setServerToken(hash, {"login": 'bid_' + login})
return context.REQUEST.RESPONSE.redirect(context.getWebSiteValue().absolute_url())
