portal = context.getPortalObject()
computer = context
maximum_days = 31
now_date = DateTime()

if (now_date - computer.getCreationDate()) < maximum_days:
  # This computer was created recently skip
  return True

memcached_dict = portal.portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

# Check if there is some information in memcached
try:
  d = memcached_dict[computer.getReference()]
except KeyError:
  message_dict = {}
else:
  message_dict = json.loads(d)

if message_dict.has_key('created_at'):
  contact_date = DateTime(message_dict.get('created_at').encode('utf-8'))
  return (now_date - contact_date) < maximum_days

# If no memcached, check in consumption report
for sale_packing_list in portal.portal_catalog(
         portal_type="Sale Packing List Line",
         simulation_state="delivered",
         default_aggregate_uid=computer.getUid(),
         sort_on=[('movement.start_date', 'DESC')],
         limit=1):
  return (now_date - sale_packing_list.getStartDate()) < maximum_days

return False
