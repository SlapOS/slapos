"""Fetch computer to find witch software is installed"""
portal = context.getPortalObject()
portal_type = "Software Release"

url_string_list = context.Computer_getSoftwareReleaseUrlStringList()
if url_string_list:
  return context.portal_catalog(
    portal_type=portal_type,
    url_string=url_string_list)
else:
  return []
