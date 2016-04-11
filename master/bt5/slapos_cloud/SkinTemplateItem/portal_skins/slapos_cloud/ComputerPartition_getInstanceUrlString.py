partition = context

software_instance_list = partition.getAggregateRelatedValueList(portal_type=["Software Instance"])
for si in software_instance_list:
  obj = si.getObject()
  return "%s?editable_mode:int=1" % obj.getRelativeUrl()
