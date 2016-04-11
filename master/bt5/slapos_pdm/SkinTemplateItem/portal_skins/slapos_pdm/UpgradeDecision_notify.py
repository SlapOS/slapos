from DateTime import DateTime

if context.getSimulationState() != 'planned':
  # XXX Don't notify the ones which are not planned.
  return 

portal = context.getPortalObject()

person = context.getDestinationDecisionValue(portal_type="Person")
if not person:
  raise ValueError("Inconsistent Upgrade Decision, No Destination Decision")

hosting_subscription = context.UpgradeDecision_getHostingSubscription()
computer = context.UpgradeDecision_getComputer()
software_release = context.UpgradeDecision_getSoftwareRelease()
software_product_title = software_release.getAggregateTitle(
                               portal_type="Software Product")
reference = context.getReference()

mapping_dict = {
  'software_product_title': software_product_title,
  'upgrade_accept_link': 'Base_acceptUpgradeDecision?reference=%s' % reference,
  'upgrade_reject_link': 'Base_rejectUpgradeDecision?reference=%s' % reference,
  'software_release_name': software_release.getTitle(),
  'software_release_reference': software_release.getReference(),
  'new_software_release_url': software_release.getUrlString(),

}
if hosting_subscription is not None:
  notification_message_reference = 'slapos-upgrade-hosting-subscription.notification'
  title = "New Upgrade available for %s" % hosting_subscription.getTitle()
  mapping_dict.update(**{
     'hosting_subscription_title': hosting_subscription.getTitle(),
     'old_software_release_url': hosting_subscription.getUrlString()})


elif computer is not None:

  notification_message_reference = 'slapos-upgrade-computer.notification' 

  title = "New Software available for Installation at %s" % computer.getTitle()
  mapping_dict.update(**{'computer_title': computer.getTitle(),
                         'computer_reference': computer.getReference()})


if notification_message_reference is None:
  raise ValueError("No Notification Message")

notification_message = portal.portal_notifications.getDocumentValue(
                 reference=notification_message_reference)

message = notification_message.asEntireHTML(
            substitution_method_parameter_dict={'mapping_dict': mapping_dict})

event = context.SupportRequest_trySendNotificationMessage(title,
              message, person.getRelativeUrl())

if event is not None:
  context.confirm()
