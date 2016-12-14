from zExceptions import Unauthorized
from AccessControl import getSecurityManager
from DateTime import DateTime
if REQUEST is not None:
  raise Unauthorized

request = context.REQUEST
portal = context.getPortalObject()

##### Starting Hardcoded Information ######
instance_xml = """<?xml version="1.0" encoding="utf-8"?>
<instance>
</instance>
"""

software_type = "RootSoftwareInstance"
#url = 'http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/heads/request.product:/software/cdn-me/software.cfg'
url = "https://lab.node.vifib.com/nexedi/slapos/raw/1.0.21/software/cdn-me/software.cfg"
shared = True

######

software_title = "'CDN ME free trial' for '%s'" % (email)


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

if len(trial_request_list) >= 30:
  return context.Base_redirect("slapos-Free.Trial.ExceedLimit.Message")


now = DateTime()

trial = context.trial_request_module.newContent(
  source_reference="RootSoftwareInstance",
  title=software_title,
  url_string=url,
  text_content=instance_xml,
  start_date=now, 
  stop_date=now + 21
  )

trial.setDefaultEmailText(email)

if batch_mode:
  return trial

return context.Base_redirect("slapos-Free.Trial.Thankyou.Message")
