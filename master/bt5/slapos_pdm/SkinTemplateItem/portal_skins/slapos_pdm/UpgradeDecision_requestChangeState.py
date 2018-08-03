upgrade_decision = context
state = upgrade_decision.getSimulationState()

message = "Transition from state %s to %s is not permitted" % (state, requested_state)
if requested_state == "started":
  if state == "confirmed":
    message = "This Upgrade Decision has been requested, it will be processed in few minutes."
    upgrade_decision.start()
elif requested_state == "rejected":
  if state in ['confirmed', 'draft', 'planned']:
    message = "Thanks Upgrade Decision has been rejected Successfully (You cannot use it anymore)."
    upgrade_decision.reject()
else:
  message = "Unknow Upgrade Decision state %r" % requested_state

return context.Base_translateString(message)
