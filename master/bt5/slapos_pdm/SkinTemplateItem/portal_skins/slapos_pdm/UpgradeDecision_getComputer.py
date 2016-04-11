computer_list = []
for decision_line in context.contentValues():
  computer_list.extend(
    decision_line.getAggregateValueList(portal_type="Computer"))

if len(computer_list) > 1: 
  raise ValueError("It is only allowed to have more them 1 Computer")

if len(computer_list) == 0:
  return None


return computer_list[0]
