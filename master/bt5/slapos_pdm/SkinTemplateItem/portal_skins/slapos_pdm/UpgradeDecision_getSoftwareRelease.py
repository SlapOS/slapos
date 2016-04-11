software_release_list = []
for decision_line in context.contentValues():
  software_release_list.extend(
    decision_line.getAggregateValueList(portal_type="Software Release"))

if len(software_release_list) > 1: 
  raise ValueError("It is only allowed to have more them 1 Software Release")

if len(software_release_list) == 0:
  return None


return software_release_list[0]
