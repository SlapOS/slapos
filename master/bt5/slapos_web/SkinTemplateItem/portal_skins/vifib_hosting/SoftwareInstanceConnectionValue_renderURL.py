v = context.getProperty('connection_value')

if v is not None and v.startswith('http'):
  return v
