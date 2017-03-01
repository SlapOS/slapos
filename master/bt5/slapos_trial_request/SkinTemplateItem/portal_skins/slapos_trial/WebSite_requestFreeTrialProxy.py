from zExceptions import Unauthorized
from AccessControl import getSecurityManager
from DateTime import DateTime
if REQUEST is not None:
  raise Unauthorized

request = context.REQUEST
portal = context.getPortalObject()

web_section = context.getWebSectionValue()

def _get(layout_property):
  return web_section.getLayoutProperty("layout_" + layout_property) 

trial_configuration = {
    "instance_xml": _get("instance_xml"),
    "base_software_title": _get("base_software_title"),
    "software_type": _get("software_type"),
    "url":_get("software_release_url"),
    "shared": _get("is_slave"),
    "subject_list": _get("subject_list"),
    "sla_xml": _get("sla_xml")
}

software_title = trial_configuration["base_software_title"] % (email)

trial_request = portal.portal_catalog.getResultValue(
              portal_type='Trial Request',
              title=software_title,
              validation_state=('draft', 'submitted',)
)

if trial_request is not None:
  return context.Base_redirect("slapos-Free.Trial.AlreadyRequested.Message")

trial_request_list = portal.portal_catalog(
              portal_type='Trial Request',
              title=software_title,
              validation_state=('validated',),
              limit=31
)

if len(trial_request_list) >= 10:
  return context.Base_redirect("slapos-Free.Trial.ExceedLimit.Message")


now = DateTime()

trial = context.trial_request_module.newContent(
  source_reference=trial_configuration["software_type"],
  title=software_title,
  url_string=trial_configuration["url"],
  text_content=trial_configuration["instance_xml"] % user_input_dict,
  start_date=now, 
  stop_date=now + 30,
  root_slave=trial_configuration["shared"],
  subject_list=trial_configuration["subject_list"]
  )

trial.setDefaultEmailText(email)

if batch_mode:
  return trial

return context.Base_redirect("slapos-Free.Trial.Thankyou.Message")
