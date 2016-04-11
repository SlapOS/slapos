from ZTUtils import make_query

from DateTime import DateTime

query_dict = dict()

if state:
  query_dict['state'] = state
person = context.ERP5Site_getAuthenticatedMemberPersonValue()
try:
  token, expires = person.Person_getBearerToken()
except ValueError:
  query_dict['error'] = 'server_error'
  if '#' in redirect_uri:
    redirect_uri += '&' + make_query(query_dict)
  else:
    redirect_uri += '#' + make_query(query_dict)
  return context.REQUEST.RESPONSE.redirect( redirect_uri )

query_dict = dict(
  access_token=token,
  token_type='bearer',
  expires_in=str(int((expires - DateTime().timeTime()))),
)
if state:
  query_dict['state'] = state

query = make_query(query_dict)

if '#' in redirect_uri:
  redirect_uri += '&' + query
else:
  redirect_uri += '#' + query
return context.REQUEST.RESPONSE.redirect( redirect_uri )
