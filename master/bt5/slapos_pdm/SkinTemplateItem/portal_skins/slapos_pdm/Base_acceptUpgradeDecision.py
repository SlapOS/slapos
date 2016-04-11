if reference is None:
  raise ValueError("Missing Reference")

portal = context.getPortalObject()

upgrade_decision_list = portal.portal_catalog(
  portal_type="Upgrade Decision", 
  reference=reference, limit=2)

if not len(upgrade_decision_list):
  return context.Base_redirect("", 
    keep_items={"portal_status_message": 
       context.Base_translateString("Unable to find the Upgrade Decision.")})

if len(upgrade_decision_list) > 1:
  raise ValueError("Duplicated reference for %s. Please contact site administrators." % reference)

upgrade_decision = upgrade_decision_list[0]

if upgrade_decision.getSimulationState() in ['draft', 'planned']:
  message = "Sorry, the upgrade is not possible yet!"

elif upgrade_decision.getSimulationState() in ['cancelled', 'rejected']:
  message = "Sorry, the upgrade is not possble, Upgrade Decision was Canceled or Rejected!"

elif upgrade_decision.getSimulationState() == 'started':
  message = "This Upgrade Decision is already Started."

elif upgrade_decision.getSimulationState() in ['stopped', 'delivered']:
  message = "This Upgrade Decision has been already processed."

elif upgrade_decision.getSimulationState() == 'confirmed':
  message = "This Upgrade Decision has been requested, it will be processed in few minutes."
  upgrade_decision.start()

return context.Base_redirect("", 
    keep_items={"portal_status_message": 
       context.Base_translateString(message)})
