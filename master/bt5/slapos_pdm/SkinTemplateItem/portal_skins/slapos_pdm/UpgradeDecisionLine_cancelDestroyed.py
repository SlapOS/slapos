software_instance = context.getAggregateValue(portal_type="Hosting Subscription")
if software_instance is not None and software_instance.getSlapState() == "destroy_requested":
  context.getParentValue().cancel()
