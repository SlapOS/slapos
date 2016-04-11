# beware: the configuration of OrderBuilder_generateSlapOSAggregatedMovementList shall
# provide small amounts of movements
person_delivery_mapping = {}
portal = context.getPortalObject()

specialise = portal.portal_preferences.getPreferredAggregatedSaleTradeCondition()
for movement in movement_list:
  person = movement.getDestinationValue()
  try:
    delivery = person_delivery_mapping[person]
  except KeyError:
    delivery = person.Person_getAggregatedDelivery()
    if delivery is None or delivery.getSimulationState() != 'confirmed':
      delivery = portal.sale_packing_list_module.newContent(
        portal_type='Sale Packing List',
        source=movement.getDestination(),
        destination=movement.getDestination(),
        source_section=movement.getSourceSection(),
        destination_section=movement.getDestination(),
        destination_decision=movement.getDestination(),
        specialise=specialise,
        price_currency=movement.getPriceCurrency()
      )
      delivery.confirm('New aggregated delivery.')
      person.Person_setAggregatedDelivery(delivery)
    person_delivery_mapping[person] = delivery
return person_delivery_mapping.values()
