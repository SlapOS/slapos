hosting_subscription_list = []
for decision_line in context.contentValues():
  hosting_subscription_list.extend(
    decision_line.getAggregateValueList(portal_type="Hosting Subscription"))

if len(hosting_subscription_list) > 1: 
  raise ValueError("It is only allowed to have more them 1 Hosting Subscription")

if len(hosting_subscription_list) == 0:
  return None


return hosting_subscription_list[0]
