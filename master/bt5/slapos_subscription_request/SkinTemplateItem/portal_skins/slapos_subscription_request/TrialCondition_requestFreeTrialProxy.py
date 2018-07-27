from zExceptions import Unauthorized
from DateTime import DateTime
import json
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()

trial_configuration = {
    "instance_xml": context.getTextContent(),
    "title": "%s for %s" % (context.getTitle(), email),
    "software_type": context.getSourceReference(),
    "url": context.getUrlString(),
    "shared": context.getRootSlave(),
    "subject_list": context.getSubjectList(),
    "sla_xml": context.getSlaXml()
}

software_title = trial_configuration["title"]

trial_request = portal.portal_catalog.getResultValue(
              portal_type='Trial Request',
              title=software_title,
              validation_state=('draft', 'submitted',)
)

if trial_request is not None:
  return json.dumps("already-requested")

trial_request_list = portal.portal_catalog(
              portal_type='Trial Request',
              title=software_title,
              validation_state=('validated',),
              limit=31
)

if len(trial_request_list) >= 10:
  return json.dumps("exceed-limit")

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

return json.dumps("thank-you")
