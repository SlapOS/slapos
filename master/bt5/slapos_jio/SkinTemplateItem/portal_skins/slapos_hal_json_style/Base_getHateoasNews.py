import json
from DateTime import DateTime

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')
try:
  d = memcached_dict[document.getReference()]
except KeyError:
  d = {
    "user": "SlapOS Master",
    "text": "#error no data found for %s" % document.getReference(),
    "no_data": 1
  }
else:
  d = json.loads(d)
  last_contact = DateTime(d.get('created_at'))
  d["no_data_since_15_minutes"] = 0
  d["no_data_since_5_minutes"] = 0
  if (DateTime() - last_contact) > 0.005:
    d["no_data_since_15_minutes"] = 1
    d["no_data_since_5_minutes"] = 1
  elif (DateTime() - last_contact) > 0.0025:
    d["no_data_since_5_minutes"] = 1

return d
