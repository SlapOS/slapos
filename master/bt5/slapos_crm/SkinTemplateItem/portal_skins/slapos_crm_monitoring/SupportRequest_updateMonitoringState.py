if context.getSimulationState() == "invalidated":
  return

document = context.getAggregateValue()

if document is None:
  return 

if document.getPortalType() == "Computer":
  return context.SupportRequest_updateMonitoringComputerState()

if document.getPortalType() == "Hosting Subscription":
  if document.getSlapState() == "destroy_requested":
    return context.SupportRequest_updateMonitoringDestroyRequestedState()
  return context.SupportRequest_updateMonitoringHostingSubscriptionState()
