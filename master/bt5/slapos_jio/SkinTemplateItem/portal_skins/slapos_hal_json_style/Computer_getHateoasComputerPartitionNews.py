if REQUEST is not None:
  raise Unauthorized

computer_partition_dict = { }
for computer_partition in context.objectValues(portal_type="Computer Partition"):
  software_instance = computer_partition.getAggregateRelatedValue(portal_type="Software Instance")
  if software_instance is not None:
    computer_partition_dict[computer_partition.getTitle()] = context.Base_getHateoasNews(software_instance)

return computer_partition_dict
