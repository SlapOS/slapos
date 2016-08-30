from Products.ERP5Type.Document import newTempDocument

portal = context.getPortalObject()

person = context.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()
hosting_subscription_list = portal.portal_catalog(
                portal_type="Hosting Subscription",
                validation_state="validated",
                default_destination_section_uid=person.getUid(),
                **kw)

monitor_parameter_list = []

def getCredentialFromUrl(url_string):
  username = password = ''
  param_list = url_string.split('#')
  if len(param_list) == 2:
    parameter_string = param_list[1]
    if 'username' in parameter_string and \
       'password' in parameter_string:
      param_list = parameter_string.split('&')
      for param in param_list:
        key, value = param.split('=')
        if key == 'username':
          username = value
        elif key == 'password':
          password = value

  return (username, password,)

for hosting_subscription in hosting_subscription_list:
  if hosting_subscription.getSlapState() == 'destroy_requested':
    continue

  instance = hosting_subscription.getPredecessorValue()
  if instance is None or instance.getSlapState() == 'destroy_requested':
    continue
  parameter_dict = instance.getConnectionXmlAsDict()

  url_string = parameter_dict.get('monitor_setup_url', '') or parameter_dict.get('monitor-setup-url', '')
  if url_string:
    if parameter_dict.has_key('monitor-user') and \
        parameter_dict.has_key('monitor-password'):
      username = parameter_dict.get('monitor-user')
      password = parameter_dict.get('monitor-password')
    else:
      # get username and password from setup-url
      username, password = getCredentialFromUrl(url_string)

  else:
    continue

  parameter_entry = newTempDocument(portal, hosting_subscription.getRelativeUrl(), uid="%s_%s" % 
                                          (person.getUid(), instance.getUid()))
  parameter_entry.edit(title=hosting_subscription.getTitle(),
                       username=username,
                       password=password,
                       url_string=url_string
                      )
  monitor_parameter_list.append(parameter_entry)

return monitor_parameter_list
