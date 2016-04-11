v = context.getProperty('connection_key')

if v is not None and v.startswith('http:') or v.startswith('https:'):
  return v
