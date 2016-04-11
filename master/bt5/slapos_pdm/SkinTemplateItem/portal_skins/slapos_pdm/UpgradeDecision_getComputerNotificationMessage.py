portal = context.getPortalObject()

notification_message = portal.portal_notifications.getDocumentValue(
                 reference='slapos-upgrade-computer.notification')

title = "New Software available for Installation at %s" % computer.getTitle()
mapping_dict = {'software_product_title': software_product_title,
                'computer_title': computer.getTitle(),
                'computer_reference': computer.getReference(),
                'software_release_name': software_release.getTitle(),
                'software_release_reference': software_release.getReference(),
                'upgrade_accept_link': 
                  'Base_acceptUpgradeDecision?reference=%s' % reference,
                'upgrade_reject_link':
                  'Base_rejectUpgradeDecision?reference=%s' % reference,
                'new_software_release_url': software_release.getUrlString(),
               }


if notification_message is not None:
  message = notification_message.asEntireHTML(
             substitution_method_parameter_dict={'mapping_dict': mapping_dict})
else:
  raise ValueError("No Notification Message")

return title, message
