portal = context.getPortalObject()

portal.portal_catalog.searchAndActivate(
  method_id='HostingSubscription_requestUpdateOpenSaleOrder',
  portal_type="Hosting Subscription",
  causality_state="diverged",
  activate_kw={'tag': tag, 'priority': 2},
  activity_count=10,
  packet_size=1, # HostingSubscription_trigger_Person_storeOpenSaleOrderJournal
)

context.activate(after_tag=tag).getId()
