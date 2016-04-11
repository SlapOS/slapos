software_installation = context
portal = context.getPortalObject()

url_string = ""
software_release = portal.portal_catalog.getResultValue(
      portal_type='Software Release',
      url_string=software_installation.getUrlString()
)
if software_release:
  url_string = "%s?editable_mode:int=1" % software_release.getAbsoluteUrl()

return url_string
