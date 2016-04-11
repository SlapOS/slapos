"""This scripts set ups role of aggregate related Software Instance

This is simple implementation, instead of generic related category with portal type,
which would not be configurable in Role Definition anyway."""

category_list = []

if obj is None:
  return []

software_instance_list = obj.getPortalObject().portal_catalog(
  portal_type='Software Instance',
  default_aggregate_uid=obj.getUid(),
  limit=2
)

if len(software_instance_list) == 1:
  hosting_subscription = software_instance_list[0].getSpecialise(portal_type='Hosting Subscription')
  for base_category in base_category_list:
    category_list.append({base_category: hosting_subscription})

return category_list
