from DateTime import DateTime
import json

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

try:
  d = memcached_dict[context.getReference()]
except KeyError:
  # Information not available
  return None

d = json.loads(d)
result = d['text']
last_contact = DateTime(d.get('created_at'))

# Optimise by checking memcache information first.
if result.startswith('#error '):
  return last_contact

return None
