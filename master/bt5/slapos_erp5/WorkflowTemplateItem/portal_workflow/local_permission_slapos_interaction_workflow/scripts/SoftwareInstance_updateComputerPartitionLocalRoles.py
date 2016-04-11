portal_type_list = ['Computer Partition']
software_instance = state_change['object']
after_tag = (software_instance.getPath(), ('immediateReindexObject', 'recursiveImmediateReindexObject'))
for object_ in software_instance.getAggregateValueList(portal_type=portal_type_list):
  object_.activate(after_path_and_method_id=after_tag).updateLocalRolesOnSecurityGroups()
