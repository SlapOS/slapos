portal_catalog = context.getPortalObject().portal_catalog
from DateTime import DateTime
method_kw = {}
method_kw.update(
  maximum_balance=context.portal_preferences.getPreferredMaximumBalance(),
  maximum_due_date=(DateTime() - context.portal_preferences.getPreferredMaximumDueDay()).Date(),
  simulation_state=context.getPortalCurrentInventoryStateList() + context.getPortalTransitInventoryStateList(),
  ongoing_simulation_state=context.getPortalFutureInventoryStateList() + context.getPortalReservedInventoryStateList(),
  section_uid=context.restrictedTraverse('organisation_module/vifib_internet').getUid(),
  operation='lock'
)
portal_catalog.searchAndActivate(
  method_id='Person_manageLockByBalance',
  payment_state='!= locked',
  portal_type='Person',
  activate_kw={'tag': tag},
  method_kw=method_kw
)
