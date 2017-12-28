import json
portal = context.getPortalObject()

if shared == "true":
  shared = True

if shared in ["false", "", None]:
  shared = False


if not title:
  raise ValueError("Service Title is mandatory!")

hosting_subscription = portal.portal_catalog.getResultValue(
  portal_type='Hosting Subscription',
  validation_state="validated",
  title={'query': title, 'key': 'ExactMatch'}
  )

if hosting_subscription is not None:
  raise ValueError("Instance with this name already exists")

# The URL should come from the URL Probably
url = context.getUrlString()

person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

if person is None:
  raise ValueError("You cannot request without been logged in as a user.")

if software_type in [None, ""]:
  software_type = "RootSoftwareInstance"

request_kw = {}
request_kw.update(
  software_release=url,
  software_title=title,
  software_type=software_type,
  instance_xml=instance_xml,
  sla_xml="",
  shared=shared,
  state="started",
)

sla_xml = ""

for sla_category_id, sla_category in [
  ('computer_guid', computer_guid),
]:
  if sla_category:
    sla_xml += '<parameter id="%s">%s</parameter>' % (sla_category_id, sla_category)

if sla_xml:
  request_kw['sla_xml'] = """<?xml version='1.0' encoding='utf-8'?>
<instance>
%s
</instance>""" % sla_xml

person.requestSoftwareInstance(**request_kw)

return json.dumps(context.REQUEST.get('request_hosting_subscription').getRelativeUrl())
