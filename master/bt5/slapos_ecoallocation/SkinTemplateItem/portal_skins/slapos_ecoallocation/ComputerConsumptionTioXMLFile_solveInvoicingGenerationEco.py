from zExceptions import Unauthorized
if REQUEST is not None:
  pass #raise Unauthorized

document = context
portal = document.getPortalObject()
result = []

tioxml_dict = document.ComputerConsumptionTioXMLFile_parseXml()
if tioxml_dict is None:
  document.reject(comment="Not usable TioXML data")
else:
  packing_list_dict = {}
  for movement_dict in tioxml_dict["movement"]:
    reference = movement_dict['reference']
    if reference in packing_list_dict:
      packing_list_dict[reference].append(movement_dict)
    else:
      packing_list_dict[reference] = [movement_dict]

  computer = context.getContributorValue(portal_type="Computer")
  for reference, movement_list in packing_list_dict.items():

    # Time to create the PL
    delivery_template = portal.restrictedTraverse(
        portal.portal_preferences.getPreferredInstanceDeliveryTemplate())
    delivery = delivery_template.Base_createCloneDocument(batch_mode=1)

    # It had been reported for the computer itself so it is pure
    # informative.
    if computer.getReference() == reference:
      person = computer.getSourceAdministrationValue(portal_type="Person")
      aggregate_value_list = [computer]
      delivery_title = "%s Information Report" % computer.getReference()
    else:
      if reference.startswith("slapuser"):
        reference = reference.replace("slapuser", "slappart") 
      # Find the partition / software instance / user
      partition = portal.portal_catalog.getResultValue(
        parent_uid=computer.getUid(),
        reference=reference,
        portal_type="Computer Partition",
        validation_state="validated")
      assert partition.getSlapState() == 'busy'

      instance = portal.portal_catalog.getResultValue(
        default_aggregate_uid=partition.getUid(),
        portal_type="Software Instance",
        validation_state="validated")

      subscription = instance.getSpecialiseValue(
        portal_type="Hosting Subscription")

      person = subscription.getDestinationSectionValue(
        portal_type="Person")
        
      aggregate_value_list = [partition, instance, subscription]
      delivery_title = "%s Consumption Usage" % instance.getReference()

    delivery.edit(
      title=delivery_title,
      destination=person.getRelativeUrl(),
      destination_decision=person.getRelativeUrl(),
      start_date=context.getCreationDate(),
    )

    result.append(delivery.getRelativeUrl())

    for movement in movement_list:
      service = portal.restrictedTraverse(movement['resource'])
      delivery.newContent(
        portal_type="Sale Packing List Line",
        title=movement['title'],
        quantity=movement['quantity'],
        aggregate_value_list=aggregate_value_list,
        resource_value=service,
        quantity_unit=service.getQuantityUnit(),
      )
    delivery.confirm(comment="Created from %s" % context.getRelativeUrl())
    delivery.start()
    delivery.stop()
    delivery.deliver()
    delivery.startBuilding()

  document.share(comment="Created packing list: %s" % result)

return result
