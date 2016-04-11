if not context.portal_membership.isAnonymousUser() and context.REQUEST.get('redirect_after_login') is not None:
  context.REQUEST.RESPONSE.expireCookie('redirect_after_login', path='/')
  return context.REQUEST.RESPONSE.redirect( context.REQUEST.get('redirect_after_login') )

elif not context.portal_membership.isAnonymousUser():
  return context.Base_redirect("myspace")

else:
  return context.Base_redirect("login_form")
