instance = context

if (instance.getSlapState() != "destroy_requested"):
  hosting_subscription = instance.getSpecialiseValue(portal_type="Hosting Subscription")
  if (hosting_subscription.getValidationState() == "archived"):
    # Buildout didn't propagate the destruction request
    requester = instance.getPredecessorRelatedValue()
    
    if instance.getPortalType() == 'Software Instance':
      is_slave = False
    elif instance.getPortalType() == 'Slave Instance':
      is_slave = True
    else:
      raise NotImplementedError, "Unknown portal type %s of %s" % \
        (instance.getPortalType(), instance.getRelativeUrl())

    if requester is None:
      # This instance has no predecessor (link removed) and should be trashed
      promise_kw = {
        'instance_xml': instance.getTextContent(),
        'software_type': instance.getSourceReference(),
        'sla_xml': instance.getSlaXml(),
        'software_release': instance.getUrlString(),
        'shared': is_slave,
      }
      instance.requestDestroy(**promise_kw)
      # Unlink all children of this instance
      instance.edit(predecessor="", comment="Destroyed garbage collector!")
    elif (instance.getRelativeUrl() in requester.getPredecessorList()) and \
      (requester.getSlapState() == "destroy_requested"):
      # For security, only destroyed if parent is also destroyed

      requester.requestInstance(
        software_release=instance.getUrlString(),
        software_title=instance.getTitle(),
        software_type=instance.getSourceReference(),
        instance_xml=instance.getTextContent(),
        sla_xml=instance.getSlaXml(),
        shared=is_slave,
        state="destroyed",
        comment="Garbage collect %s" % instance.getRelativeUrl()
      )
