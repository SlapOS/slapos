from ZTUtils import make_query

query_dict = dict()

if state:
  query_dict['state'] = state

query_dict['error'] = 'access_denied'
if '#' in redirect_uri:
  redirect_uri += '&' + make_query(query_dict)
else:
  redirect_uri += '#' + make_query(query_dict)
return context.REQUEST.RESPONSE.redirect( redirect_uri )
