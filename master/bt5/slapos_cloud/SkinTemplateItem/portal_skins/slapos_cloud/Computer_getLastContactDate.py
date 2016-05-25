from DateTime import DateTime
import json

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

try:
  d = memcached_dict[context.getReference()]
except KeyError:
  return "Computer didn't contact the server"
else:
  log_dict = json.loads(d)
  date = DateTime(log_dict['created_at'])
  return date.strftime('%Y/%m/%d %H:%M')
