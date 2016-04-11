return True

# Disabled functionality
#section_uid = context.getSourceSectionUid()
#customer_uid = context.getDestinationSectionUid()
#simulation_state = context.getPortalCurrentInventoryStateList() + context.getPortalTransitInventoryStateList()
#balance = context.portal_simulation.getInventoryAssetPrice(
#  node_category_strict_membership='account_type/asset/receivable',
#  simulation_state=simulation_state,
#  section_uid=section_uid,
#  mirror_section_uid=customer_uid)
#return balance <= 0.
