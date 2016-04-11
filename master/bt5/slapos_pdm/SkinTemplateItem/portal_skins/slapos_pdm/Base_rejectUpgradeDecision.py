if reference is None:
  raise ValueError("Missing Reference")

portal = context.getPortalObject()

upgrade_decision_list = portal.portal_catalog(
  portal_type="Upgrade Decision", 
  reference=reference, limit=2)

if len(upgrade_decision_list) == 0:
  return context.Base_redirect("", 
    keep_items={"portal_status_message": 
       context.Base_translateString("Unable to find the Upgrade Decision.")})

if len(upgrade_decision_list) > 1:
  raise ValueError("Duplicated reference for %s. Please contact site administrators." % reference)

upgrade_decision = upgrade_decision_list[0]


if upgrade_decision.getSimulationState() in ['cancelled', 'rejected']:
  message = "Upgrade Decision is already Rejected!"

elif upgrade_decision.getSimulationState() == 'started':
  message = "Sorry, This Upgrade Decision is already Started, you cannot reject it anymore."

elif upgrade_decision.getSimulationState() in ['stopped', 'delivered']:
  message = "Sorry, this Upgrade Decision has been already processed."

elif upgrade_decision.getSimulationState() in ['confirmed', 'draft', 'planned']:
  message = "Thanks Upgrade Decision has been rejected Successfully (You cannot use it anymore)."
  upgrade_decision.reject()

return context.Base_redirect("", 
    keep_items={"portal_status_message": 
       context.Base_translateString(message)})
