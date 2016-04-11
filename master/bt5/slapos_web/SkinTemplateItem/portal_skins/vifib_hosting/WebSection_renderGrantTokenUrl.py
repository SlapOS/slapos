from ZTUtils import make_query
g = context.REQUEST.get


return './WebSection_grantToken?' + make_query(dict(
  redirect_uri=g('redirect_uri', ''),
  client_id=g('client_id', ''),
  state=g('state', ''),
  ))
