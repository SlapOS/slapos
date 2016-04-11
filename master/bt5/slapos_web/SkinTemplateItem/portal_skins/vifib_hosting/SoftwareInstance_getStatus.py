"""Dirty script to return Software Instance state"""
import json
state = context.getSlapState()
has_partition = context.getAggregate(portal_type="Computer Partition")
result = 'Unable to calculate the status...'
if has_partition:
  try:
    memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
      key_prefix='slap_tool',
      plugin_path='portal_memcached/default_memcached_plugin')
    try:
      d = memcached_dict[context.getReference()]
    except KeyError:
      result = context.getSlapStateTitle()
    else:
      d = json.loads(d)
      result = d['text']
      if result.startswith('#access '):
        result = result[len('#access '):]

  except Exception:
    raise
    result = 'There is system issue, please try again later.'

else:
  if state in ["start_requested", "stop_requested"]:
    result = 'Looking for a free partition'
  elif state in ["destroy_requested"]:
    result = 'Destroyed'

return result
