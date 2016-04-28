portal = context.getPortalObject()

if shared == "true":
  shared = True
  
if shared == "false":
  shared = False

if not service_title:
  raise ValueError("Service Title is mandatory!")

keep_item_dict = {}

if software_type is not None:
  keep_item_dict['software_type'] = software_type

if software_type is not None:
  keep_item_dict['parameter_hash'] = parameter_hash

if instance_xml == "ERROR":
  keep_item_dict.update({'portal_status_message':context.Base_translateString(
                          "Your parameters are contains errors, please update it.")})
  return context.Base_redirect(dialog_id,
                        keep_items=keep_item_dict)

hosting_subscription = portal.portal_catalog.getResultValue(
  portal_type='Hosting Subscription',
  validation_state="validated",
  select_expression='title',
  title={'query': service_title, 'key': 'ExactMatch'}
  )

if hosting_subscription is not None:
  return context.Base_redirect(dialog_id,
                        keep_items={'portal_status_message':context.Base_translateString(
                          "You already have service named ${service_title}. Please choose different unique name.", mapping={'service_title': service_title})})


url = context.getUrlString()

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

if person is None:
  raise ValueError("You cannot request without been logged in as a user.")
  
if software_type in [None, ""]:
  software_type = "RootSoftwareInstance"

request_kw = {}
request_kw.update(
  software_release=url,
  software_title=service_title,
  software_type=software_type,
  instance_xml=instance_xml,
  sla_xml="",
  shared=shared,
  state="started",
)

sla_xml = ""

for sla_category_id, sla_category in [
  ('cpu_core', cpu_core),
  ('cpu_frequency', cpu_frequency),
  ('cpu_type', cpu_type),
  ('local_area_network_type', local_area_network_type),
  ('memory_size', memory_size),
  ('memory_type', memory_type),
  ('region', region),
  ('storage_capacity', storage_capacity),
  ('storage_interface', storage_interface),
  ('storage_redundancy', storage_redundancy),
  ('computer_guid', computer_guid),
  ('group', group),
]:
  if sla_category:
    sla_xml += '<parameter id="%s">%s</parameter>' % (sla_category_id, sla_category)

if sla_xml:
  request_kw['sla_xml'] = """<?xml version='1.0' encoding='utf-8'?>
<instance>
%s
</instance>""" % sla_xml

person.requestSoftwareInstance(**request_kw)

message = context.Base_translateString("Your instance is under creation. Please wait few minutes for partitions to appear.")
return context.REQUEST.get('request_hosting_subscription').Base_redirect(keep_items={'portal_status_message': message})
