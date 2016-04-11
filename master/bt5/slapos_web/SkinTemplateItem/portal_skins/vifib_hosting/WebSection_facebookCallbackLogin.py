get = context.REQUEST.get

def handleError():
  context.Base_redirect('login_form', keep_items={"portal_status_message": "There was problem with Facebook login: %s. Please try again later." % get('error_description')})

if get('error') is not None:
  return handleError()
elif get('code') is not None:
  access_token_dict = context.Facebook_getAccessTokenFromCode(get('code'), context.absolute_url())
  if access_token_dict is not None:
    access_token = access_token_dict['access_token']
    access_token_dict['login'] = 'fb_' + context.Facebook_getUserId(access_token)
    hash = context.Base_getHMAC(access_token, access_token)
    context.REQUEST.RESPONSE.setCookie('__ac_facebook_hash', hash, path='/')
    context.Facebook_setServerToken(hash, access_token_dict)
    return context.REQUEST.RESPONSE.redirect(context.getWebSiteValue().absolute_url())
return handleError()
