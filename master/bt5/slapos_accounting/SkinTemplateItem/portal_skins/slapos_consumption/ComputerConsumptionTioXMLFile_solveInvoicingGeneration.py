from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

document = context
portal = document.getPortalObject()
result = []

if context.getValidationState() in ["cancelled", "shared"]:
  return

try:
  tioxml_dict = document.ComputerConsumptionTioXMLFile_parseXml()
except KeyError:
  document.reject(comment="Fail")
  return 

if tioxml_dict is None:
  document.reject(comment="Not usable TioXML data")
else:

  computer = context.getContributorValue(portal_type="Computer")
  delivery_title = tioxml_dict['title']

  movement_list = []
  for movement in tioxml_dict["movement"]:
    reference = movement['reference']

    # It had been reported for the computer itself so it is pure
    # informative.
    if computer.getReference() == reference:
      aggregate_value_list = [computer]
      person = computer.getSourceAdministrationValue(portal_type="Person")
    else:
      if reference.startswith("slapuser"):
        reference = reference.replace("slapuser", "slappart") 
      # Find the partition / software instance / user
      partition = portal.portal_catalog.getResultValue(
        parent_uid=computer.getUid(),
        reference=reference,
        portal_type="Computer Partition",
        validation_state="validated")

      if partition.getSlapState() != 'busy':
        continue

      assert partition.getSlapState() == 'busy', "partition %s is not busy" % reference

      instance = portal.portal_catalog.getResultValue(
        default_aggregate_uid=partition.getUid(),
        portal_type="Software Instance",
        validation_state="validated")

      if instance is None:
        # There is no software instance for this partition anymore
        # so we just skip this partial consumption.
        continue

      subscription = instance.getSpecialiseValue(
        portal_type="Hosting Subscription")

      try:
        person = subscription.getDestinationSectionValue(
          portal_type="Person")
      except:
        raise ValueError(instance.getRelativeUrl())

      aggregate_value_list = [partition, instance, subscription]

    movement_list.append(dict(
                        title=movement['title'],
                        quantity=movement['quantity'],
                        aggregate_value_list=aggregate_value_list,
                        resource=movement['resource'],
                        person=person.getRelativeUrl()
                    )
        )

  # Time to create the PL
  person = computer.getSourceAdministrationValue(portal_type="Person")
  delivery_template = portal.restrictedTraverse(
      portal.portal_preferences.getPreferredInstanceDeliveryTemplate())
  delivery = delivery_template.Base_createCloneDocument(batch_mode=1)

  delivery.edit(
    title=delivery_title,
    destination=person.getRelativeUrl(),
    destination_decision=person.getRelativeUrl(),
    start_date=context.getCreationDate(),
  )

  for movement in movement_list:
    service = portal.restrictedTraverse(movement['resource'])
    delivery.newContent(
      portal_type="Sale Packing List Line",
      title=movement['title'],
      quantity=movement['quantity'],
      aggregate_value_list=movement['aggregate_value_list'],
      destination=movement['person'],
      destination_decision=movement['person'],
      destination_section=movement['person'],
      resource_value=service,
      quantity_unit=service.getQuantityUnit(),
    )
  delivery.confirm(comment="Created from %s" % context.getRelativeUrl())
  delivery.start()
  delivery.stop()
  delivery.deliver()
  delivery.startBuilding()

  result.append(delivery.getRelativeUrl())
  document.share(comment="Created packing list: %s" % result)

return result
