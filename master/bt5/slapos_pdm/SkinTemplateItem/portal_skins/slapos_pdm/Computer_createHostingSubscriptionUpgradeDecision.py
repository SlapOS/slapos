from DateTime import DateTime
portal = context.getPortalObject()

partition_list = portal.portal_catalog(portal_type='Computer Partition',
                                        free_for_request=0,
                                        parent_uid=context.getUid())
valid_slap_state = ['start_requested', 'stop_requested']

hosting_subscription_list = []
upgrade_decision_list = []
for partition in partition_list:
  software_instance = partition.getAggregateRelatedValue(
                            portal_type='Software Instance')
  if not software_instance:
    continue

  hosting_subscription = software_instance.getSpecialiseValue(
                portal_type='Hosting Subscription')
  if hosting_subscription and hosting_subscription.getSlapState() \
      in valid_slap_state and not \
      hosting_subscription in hosting_subscription_list:
    hosting_subscription_list.append(hosting_subscription)
  else:
    continue
  newer_release = hosting_subscription.\
                    HostingSubscription_getUpgradableSoftwareRelease()
  if newer_release is None:
    continue

  decision_in_progress = newer_release.\
      SoftwareRelease_getUpgradeDecisionInProgress(hosting_subscription.getUid())
  
  if decision_in_progress and \
      not decision_in_progress.UpgradeDecision_tryToCancel(
        newer_release.getUrlString()):
    continue
  
  upgrade_decision = newer_release.SoftwareRelease_createUpgradeDecision(
    source_url=hosting_subscription.getRelativeUrl(),
    title='A new upgrade is available for %s' % hosting_subscription.getTitle()
  )
  upgrade_decision.plan()
  upgrade_decision.setStartDate(DateTime())
  upgrade_decision_list.append(upgrade_decision)

return upgrade_decision_list
