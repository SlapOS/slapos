from DateTime import DateTime
computer = context
portal = context.getPortalObject()

full_software_release_list = [si.getUrlString() for si in
              portal.portal_catalog(
                portal_type='Software Installation',
                default_aggregate_uid=computer.getUid(),
                validation_state='validated'
              ) if si.getSlapState() == 'start_requested']

if len(full_software_release_list) == 0:
  return
# group SR by Software Product to avoid two upgrade Decision for the same product
software_release_list = portal.portal_catalog(
                          portal_type='Software Release',
                          url_string=full_software_release_list,
                          group_by='default_aggregate_uid'
                        )
upgrade_decision_list = []
for software_release in software_release_list:
  software_product_reference = software_release.getAggregateReference()
  if software_product_reference in [None, ""]:
    continue
  
  sorted_list = portal.SoftwareProduct_getSortedSoftwareReleaseList(
    software_product_reference=software_product_reference)
  
  # Check if there is a new version of this software Product
  if sorted_list and \
      sorted_list[0].getUrlString() not in full_software_release_list:
    
    newer_release = sorted_list[0]
    title = 'A new version of %s is available for %s' % \
                        (software_product_reference, context.getTitle()) 
    # If exist upgrade decision in progress try to cancel it
    decision_in_progress = newer_release.\
            SoftwareRelease_getUpgradeDecisionInProgress(computer.getUid())
    if decision_in_progress and \
        not decision_in_progress.UpgradeDecision_tryToCancel(
          newer_release.getUrlString()):
      continue
  
    upgrade_decision = newer_release.SoftwareRelease_createUpgradeDecision(
        source_url=computer.getRelativeUrl(),
        title=title)
        
    if context.getAllocationScope() in ["open/public", "open/friend"]:
      upgrade_decision.start()
    elif context.getAllocationScope() in ["open/personal"]:
      upgrade_decision.plan()
    
    upgrade_decision.setStartDate(DateTime())
    upgrade_decision_list.append(upgrade_decision)

return upgrade_decision_list
