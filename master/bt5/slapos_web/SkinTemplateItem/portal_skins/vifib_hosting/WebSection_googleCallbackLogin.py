get = context.REQUEST.get

def handleError():
  context.Base_redirect('login_form', keep_items={"portal_status_message": "There was problem with Google login: %s. Please try again later." % get('error')})

if get('error') is not None:
  return handleError()
elif get('code') is not None:
  access_token_dict = context.Google_getAccessTokenFromCode(get('code'), context.absolute_url())
  if access_token_dict is not None:
    access_token = access_token_dict['access_token'].encode('utf-8')
    access_token_dict['login'] = 'go_' + context.Google_getUserId(access_token)
    hash = context.Base_getHMAC(access_token, access_token)
    context.REQUEST.RESPONSE.setCookie('__ac_google_hash', hash, path='/')
    context.Google_setServerToken(hash, access_token_dict)
    return context.REQUEST.RESPONSE.redirect(context.getWebSiteValue().absolute_url())
return handleError()
