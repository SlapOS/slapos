if context.UpgradeDecision_upgradeHostingSubscription():
  return True

if context.UpgradeDecision_upgradeComputer():
  return True

return False
