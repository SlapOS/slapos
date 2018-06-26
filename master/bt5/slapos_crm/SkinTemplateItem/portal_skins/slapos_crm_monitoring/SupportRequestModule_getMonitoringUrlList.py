from Products.ERP5Type.Document import newTempDocument

portal = context.getPortalObject()

support_request_list = portal.portal_catalog(
                portal_type="Support Request",
                simulation_state=["validated", "Suspended"],
                )

hosting_subscription_list = []
for support_request in support_request_list:
  hosting_subscription_list.append(
    support_request.getAggregateValue(portal_type="Hosting Subscription"))

monitor_instance_list = []

def getMonitorUrlFromUrlString(parameter_string):
  if 'url=' in parameter_string:
    param_list = parameter_string.split('&')
    for param in param_list:
      key, value = param.split('=')
      if key == 'url':
        return value

for hosting_subscription in hosting_subscription_list:

  if hosting_subscription is None:
    continue

  if hosting_subscription.getSlapState() == 'destroy_requested':
    continue

  instance = hosting_subscription.getPredecessorValue()
  if instance is None or instance.getSlapState() in ('destroy_requested', 'stop_requested'):
    o = newTempDocument(portal, "uid_%s" % instance.getId())
    o.edit(title=instance.getTitle(), monitor_url=instance.getSlapState())
    monitor_instance_list.append(o)
    continue

  parameter_dict = instance.getConnectionXmlAsDict()

  url_string = parameter_dict.get('monitor_setup_url', '') or parameter_dict.get('monitor-setup-url', '')
  if url_string:
    param_list = url_string.split('#')
    if len(param_list) != 2:
      # bad or unknown url
      continue

    o = newTempDocument(portal, "uid_%s" % instance.getId())
    o.edit(title=instance.getTitle(), monitor_url=url_string)
    monitor_instance_list.append(o)

return monitor_instance_list
