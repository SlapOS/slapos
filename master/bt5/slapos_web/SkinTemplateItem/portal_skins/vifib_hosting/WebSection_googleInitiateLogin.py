from ZTUtils import make_query
query = make_query({
    'response_type': 'code',
    'client_id': context.portal_preferences.getPreferredVifibGoogleApplicationId(),
    'redirect_uri': context.google_callback.absolute_url(),
    'scope': 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email'
})

context.REQUEST.RESPONSE.redirect('''https://accounts.google.com/o/oauth2/auth?''' + query)
