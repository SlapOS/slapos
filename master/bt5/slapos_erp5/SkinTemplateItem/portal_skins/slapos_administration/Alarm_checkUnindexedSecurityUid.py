from Products.CMFActivity.ActiveResult import ActiveResult

portal = context.getPortalObject()
active_process = context.newActiveProcess().getRelativeUrl()

missing_security_uid_list = portal.z_search_unindexed_security_uid()

if len(missing_security_uid_list) > 0:
  if fixit:
    summary = "Security UIDs were inconsistent (fixing it)"
    portal.z_refresh_roles_and_users()
  else:
    summary="Security UIDs are inconsistent"
     
  active_process.postResult(ActiveResult(
         summary=summary,
         severity=100,
         detail="Missing Security Uid List: %s " % missing_security_uid_list))
