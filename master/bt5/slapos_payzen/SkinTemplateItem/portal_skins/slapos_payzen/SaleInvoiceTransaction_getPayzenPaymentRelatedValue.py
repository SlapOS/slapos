portal = context.getPortalObject()
return portal.portal_catalog.getResultValue(
    portal_type="Payment Transaction",
    simulation_state="started",
    default_causality_uid=context.getUid(),
    default_payment_mode_uid=portal.portal_categories.payment_mode.payzen.getUid(),
  )
