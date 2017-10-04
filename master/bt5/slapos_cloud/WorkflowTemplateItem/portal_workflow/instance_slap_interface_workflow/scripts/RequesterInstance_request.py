requester_instance = state_change['object']
portal = requester_instance.getPortalObject()
# Get required arguments
kwargs = state_change.kwargs

# Required args
# Raise TypeError if all parameters are not provided
try:
  software_release_url_string = kwargs['software_release']
  software_title = kwargs["software_title"]
  software_type = kwargs["software_type"]
  instance_xml = kwargs["instance_xml"]
  sla_xml = kwargs["sla_xml"]
  is_slave = kwargs["shared"]
  root_state = kwargs["state"]
except KeyError:
  raise
  raise TypeError, "RequesterInstance_request takes exactly 7 arguments"

if is_slave not in [True, False]:
  raise ValueError, "shared should be a boolean"

# Hosting subscriptin is used as the root of the instance tree
if requester_instance.getPortalType() == "Hosting Subscription":
  hosting_subscription = requester_instance
else:
  hosting_subscription = requester_instance.getSpecialiseValue(portal_type="Hosting Subscription")

# Instance can be moved from one requester to another
# Prevent creating two instances with the same title
tag = "%s_%s_inProgress" % (hosting_subscription.getUid(), software_title)
if (portal.portal_activities.countMessageWithTag(tag) > 0):
  # The software instance is already under creation but can not be fetched from catalog
  # As it is not possible to fetch informations, it is better to raise an error
  raise NotImplementedError(tag)

# graph allows to "simulate" tree change after requested operation
graph = {}
predecessor_list = hosting_subscription.getPredecessorValueList()
graph[hosting_subscription.getUid()] = [predecessor.getUid() for predecessor in predecessor_list]
while True:
  try:
    current_software_instance = predecessor_list.pop(0)
  except IndexError:
    break
  current_software_instance_predecessor_list = current_software_instance.getPredecessorValueList() or []
  graph[current_software_instance.getUid()] = [predecessor.getUid()
                                               for predecessor in current_software_instance_predecessor_list]
  predecessor_list.extend(current_software_instance_predecessor_list)

# Check if it already exists
request_software_instance_list = portal.portal_catalog(
  # Fetch all portal type, as it is not allowed to change it
  portal_type=["Software Instance", "Slave Instance"],
  title={'query': software_title, 'key': 'ExactMatch'},
  specialise_uid=hosting_subscription.getUid(),
  # Do not fetch destroyed instances
  # XXX slap_state=["start_requested", "stop_requested"],
  validation_state="validated",
  limit=2,
)
instance_count = len(request_software_instance_list)
if instance_count == 0:
  request_software_instance = None
elif instance_count == 1:
  request_software_instance = request_software_instance_list[0].getObject()
else:
  raise ValueError, "Too many instances '%s' found: %s" % (software_title, [x.path for x in request_software_instance_list])

if (request_software_instance is None):
  if (root_state == "destroyed"):
    instance_found = False
  else:
    instance_found = True
    # First time that the software instance is requested

    # Create a new one
    reference = "SOFTINST-%s" % portal.portal_ids.generateNewId(
      id_group='slap_software_instance_reference',
      id_generator='uid')

    new_content_kw = {}
    if is_slave == True:
      software_instance_portal_type = "Slave Instance"
    else:
      software_instance_portal_type = "Software Instance"
      certificate_dict = portal.portal_certificate_authority.getNewCertificate(reference)
      new_content_kw['destination_reference'] = certificate_dict['id']
      new_content_kw['ssl_key'] = certificate_dict['key']
      new_content_kw['ssl_certificate'] = certificate_dict['certificate']

    module = portal.getDefaultModule(portal_type="Software Instance")
    request_software_instance = module.newContent(
      portal_type=software_instance_portal_type,
      title=software_title,
      specialise_value=hosting_subscription,
      reference=reference,
      activate_kw={'tag': tag},
      **new_content_kw
    )
    request_software_instance.validate()
    if software_instance_portal_type == "Software Instance":
      # Include ERP5 Login so Instance become a User
      erp5_login = request_software_instance.newContent(
        portal_type="ERP5 Login",
        reference=request_software_instance.getReference())
      erp5_login = erp5_login.validate()

    graph[request_software_instance.getUid()] = []

else:
  instance_found = True
  # Update the predecessor category of the previous requester
  predecessor = request_software_instance.getPredecessorRelatedValue(portal_type="Software Instance")
  if (predecessor is None):
    if (requester_instance.getPortalType() != "Hosting Subscription"):
      raise ValueError('It is disallowed to request root software instance %s' % request_software_instance.getRelativeUrl())
    else:
      predecessor = requester_instance
  predecessor_uid_list = predecessor.getPredecessorUidList()
  predecessor_uid_list.remove(request_software_instance.getUid())
  predecessor.edit(predecessor_uid_list=predecessor_uid_list)
  graph[predecessor.getUid()] = predecessor_uid_list

if instance_found:

  # Change desired state
  promise_kw = {
    'instance_xml': instance_xml,
    'software_type': software_type,
    'sla_xml': sla_xml,
    'software_release': software_release_url_string,
    'shared': is_slave,
  }
  request_software_instance_url = request_software_instance.getRelativeUrl()
  context.REQUEST.set('request_instance', request_software_instance)
  if (root_state == "started"):
    request_software_instance.requestStart(**promise_kw)
  elif (root_state == "stopped"):
    request_software_instance.requestStop(**promise_kw)
  elif (root_state == "destroyed"):
    request_software_instance.requestDestroy(**promise_kw)
    context.REQUEST.set('request_instance', None)
  else:
    raise ValueError, "state should be started, stopped or destroyed"

  predecessor_list = requester_instance.getPredecessorList() + [request_software_instance_url]
  uniq_predecessor_list = list(set(predecessor_list))
  predecessor_list.sort()
  uniq_predecessor_list.sort()

  assert predecessor_list == uniq_predecessor_list, "%s != %s" % (predecessor_list, uniq_predecessor_list)

  # update graph to reflect requested operation
  graph[requester_instance.getUid()] = requester_instance.getPredecessorUidList() + [request_software_instance.getUid()]

  # check if all elements are still connected and if there is no cycle
  request_software_instance.checkConnected(graph, hosting_subscription.getUid())
  request_software_instance.checkNotCyclic(graph)

  requester_instance.edit(predecessor_list=predecessor_list)

else:
  context.REQUEST.set('request_instance', None)
