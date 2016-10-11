if context.getSimulationState() == "invalidated":
  return

document = context.getSourceProjectValue()

if document is None:
  return True

if document.getPortalType() == "Computer":
  return context.SupportRequest_updateMontoringComputerState()

if document.getPortalType() == "Hosting Subscription":
  return context.SupportRequest_updateMonitoringHostingSubscriptionState()
