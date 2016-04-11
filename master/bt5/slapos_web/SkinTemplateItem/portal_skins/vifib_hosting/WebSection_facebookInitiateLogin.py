from ZTUtils import make_query
query = make_query({
    'client_id': context.portal_preferences.getPreferredVifibFacebookApplicationId(),
    'redirect_uri': context.facebook_callback.absolute_url(),
    'scope': 'email'
})

context.REQUEST.RESPONSE.redirect('''https://www.facebook.com/dialog/oauth?''' + query)
