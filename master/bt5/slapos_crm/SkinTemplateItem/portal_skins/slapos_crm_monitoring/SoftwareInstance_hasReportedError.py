from DateTime import DateTime
import json

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

if context.getAggregateValue(portal_type="Computer Partition") is not None:
  try:
    d = memcached_dict[context.getReference()]
  except KeyError:
    return  

  d = json.loads(d)
  result = d['text']
  last_contact = DateTime(d.get('created_at'))

  # Optimise by checking memcache information first.
  if result.startswith('#error '):
    return last_contact

  # XXX time limit of 48 hours for run at least once.

return None
