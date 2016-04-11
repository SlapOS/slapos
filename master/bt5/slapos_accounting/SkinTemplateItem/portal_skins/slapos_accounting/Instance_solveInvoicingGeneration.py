instance = context
portal = instance.getPortalObject()
portal_workflow = portal.portal_workflow

if portal_workflow.isTransitionPossible(instance, 'converge'):
  instance.converge()

  slap_state = instance.getSlapState()

  if slap_state == 'draft':
    # Nothing to do except converging
    pass
  else:
    started = "start_requested"
    stopped = "stop_requested"
    destroyed = "destroy_requested"
    assert slap_state in [started, stopped, destroyed]

    previous_length = instance.getInvoicingSynchronizationPointer(1)
    history_list = portal_workflow.getInfoFor(ob=instance, name='history', wf_id='instance_slap_interface_workflow')
    history_length = len(history_list)
    history_entry = history_list[previous_length-1]

    # no divergence if no new history entry
    if (history_length != 1):
      assert previous_length != history_length

    setup_quantity = 0
    update_quantity = 0
    destroy_quantity = 0

    current_delivery = instance.getCausalityValue()
    if current_delivery is None:
      # No previous packing list, so, one setup should be created
      # Drop all useless draft line
      i_in_draft_state = True
      i = 0
      while i_in_draft_state:
        checking_history_entry = history_list[i]
        previous_state = checking_history_entry['slap_state']
        if previous_state != 'draft':
          i_in_draft_state = False
          previous_length = i
        else:
          setup_quantity += 1
        i += 1

    if slap_state == destroyed:
      # Check if previous pointer was already in destroyed state
      previous_state = history_entry['slap_state']
      if previous_state != destroyed:
        # Let's create destroyed packing list
        destroy_quantity = 1

    # 1 = entry to set document in draft state
    update_quantity = history_length - previous_length - setup_quantity - destroy_quantity

    # Time to create the PL
    delivery_template = portal.restrictedTraverse(
        portal.portal_preferences.getPreferredInstanceDeliveryTemplate())
    delivery = delivery_template.Base_createCloneDocument(batch_mode=1)

    hosting_subscription = instance.getSpecialiseValue(portal_type="Hosting Subscription")
    person = hosting_subscription.getDestinationSectionValue(portal_type="Person")

    delivery.edit(
      title="%s API usage" % instance.getReference(),
      destination=person.getRelativeUrl(),
      destination_decision=person.getRelativeUrl(),
      start_date=history_entry['time'],
      stop_date=portal_workflow.getInfoFor(ob=instance, name='time', wf_id='instance_slap_interface_workflow'),
    )
    line_edit_kw = {
      'aggregate_value_list': [instance, hosting_subscription],
    }

    if setup_quantity:
      delivery_line_template = portal.restrictedTraverse(
          portal.portal_preferences.getPreferredInstanceSetupMovementTemplate())
      line = delivery_line_template.Base_createCloneDocument(batch_mode=1,
          destination=delivery)
      line.edit(
        quantity=1,
        title="%s setup %s" % (instance.getReference(), setup_quantity),
        **line_edit_kw
      )

    if update_quantity > 0:
      delivery_line_template = portal.restrictedTraverse(
          portal.portal_preferences.getPreferredInstanceUpdateMovementTemplate())
      line = delivery_line_template.Base_createCloneDocument(batch_mode=1,
          destination=delivery)
      line.edit(
        quantity=update_quantity,
        title="%s updated %i times" % (instance.getReference(), update_quantity),
        **line_edit_kw
      )

    if destroy_quantity:
      delivery_line_template = portal.restrictedTraverse(
          portal.portal_preferences.getPreferredInstanceDestroyMovementTemplate())
      line = delivery_line_template.Base_createCloneDocument(batch_mode=1,
          destination=delivery)
      line.edit(
        quantity=destroy_quantity,
        title="%s destroyed" % instance.getReference(),
        **line_edit_kw
      )

    delivery.confirm()
    delivery.start()
    delivery.stop()
    delivery.deliver()
    delivery.startBuilding()

    instance.edit(
      invoicing_synchronization_pointer=history_length,
      causality_value=delivery,
    )
