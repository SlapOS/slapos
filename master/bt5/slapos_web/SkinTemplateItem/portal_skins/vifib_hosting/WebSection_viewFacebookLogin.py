base_url = context.REQUEST.other["URL"].rsplit("/",1)[0]

if context.REQUEST.form.get('callback_url') is not None:
  context.REQUEST.RESPONSE.setCookie("redirect_after_login", 
                                            context.REQUEST.form['callback_url'], 
                                            path="/")

return context.getWebSiteValue().login_with_facebook.WebSection_facebookInitiateLogin()
