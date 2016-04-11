partition = context
portal = context.getPortalObject()
image_url = ""

software_instance = partition.getAggregateRelatedValue(portal_type="Software Instance")

release = portal.portal_catalog.getResultValue(
    portal_type="Software Release",
    url_string=software_instance.getUrlString(),
)
if release is not None:
  software_product = release.getAggregateValue()
  image_url = '%s/index_html' % software_product.getDefaultImageAbsoluteUrl()

return image_url
