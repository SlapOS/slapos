person = context.getPortalObject().ERP5Site_getAuthenticatedMemberPersonValue()

if person is None or person.Person_isServiceProvider():
  return "<a href=%s/SoftwareProduct_viewSoftwareReleaseOrderDialog> Order Now </a>" % cell.absolute_url()

software_release_list = cell.SoftwareProduct_getSortedSoftwareReleaseList()

if not software_release_list:
  return "<a href=%s/SoftwareProduct_viewSoftwareReleaseOrderDialog> Order Now </a>" % cell.absolute_url()

latest_software_release = software_release_list[0]

return "<a href=%s/SoftwareRelease_viewRequestDialog> Order Now </a>" % latest_software_release.absolute_url()
