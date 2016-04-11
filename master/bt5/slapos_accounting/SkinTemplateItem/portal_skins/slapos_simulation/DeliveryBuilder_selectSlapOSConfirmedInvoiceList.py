portal_type = context.getDeliveryPortalType()
simulation_state = 'confirmed'

# use catalog to prefetch, but check later in ZODB
return [x.getObject() for x in context.getPortalObject().portal_catalog(
   portal_type=portal_type,
   # BEWARE: it works only in case of per-tree building
   default_destination_section_uid=movement_list[0].getDestinationSectionUid(),
   simulation_state=simulation_state) if x.getSimulationState() == simulation_state]
