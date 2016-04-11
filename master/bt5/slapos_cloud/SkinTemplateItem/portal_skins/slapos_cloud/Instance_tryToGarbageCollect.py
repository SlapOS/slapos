instance = context

if (instance.getSlapState() != "destroy_requested"):
  hosting_subscription = instance.getSpecialiseValue(portal_type="Hosting Subscription")
  if (hosting_subscription.getValidationState() == "archived"):
    # Buildout didn't propagate the destruction request
    requester = instance.getPredecessorRelatedValue()
    if (instance.getRelativeUrl() in requester.getPredecessorList()) and \
      (requester.getSlapState() == "destroy_requested"):
      # For security, only destroyed if parent is also destroyed

      if instance.getPortalType() == 'Software Instance':
        is_slave = False
      elif instance.getPortalType() == 'Slave Instance':
        is_slave = True
      else:
        raise NotImplementedError, "Unknown portal type %s of %s" % \
          (instance.getPortalType(), instance.getRelativeUrl())

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
