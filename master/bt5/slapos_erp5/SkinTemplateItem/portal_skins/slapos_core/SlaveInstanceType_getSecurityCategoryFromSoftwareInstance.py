"""
This script returns a list of dictionaries which represent
the security groups which a person is member of. It extracts
the categories from the current content. It is useful in the
following cases:

- calculate a security group based on a given
  category of the current object (ex. group). This
  is used for example in ERP5 DMS to calculate
  document security.

- assign local roles to a document based on
  the person which the object related to through
  a given base category (ex. destination). This
  is used for example in ERP5 Project to calculate
  Task / Task Report security.

The parameters are

  base_category_list -- list of category values we need to retrieve
  user_name          -- string obtained from getSecurityManager().getUser().getId()
  object             -- object which we want to assign roles to
  portal_type        -- portal type of object

NOTE: for now, this script requires proxy manager
"""

category_list = []

if obj is None:
  return []

partition = obj.getAggregateValue(portal_type="Computer Partition")
if partition is not None:
  software_instance = partition.getPortalObject().portal_catalog.getResultValue(
    portal_type="Software Instance", validation_state="validated", default_aggregate_uid=partition.getUid())
  if software_instance is not None:
    for base_category in base_category_list:
      category_list.append({base_category: [software_instance.getRelativeUrl()]})

return category_list
