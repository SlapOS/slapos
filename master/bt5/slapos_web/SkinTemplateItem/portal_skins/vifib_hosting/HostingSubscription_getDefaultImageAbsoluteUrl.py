from Products.ERP5Type.Cache import CachingMethod

subscription_item = context
portal = context.getPortalObject()


def getCachedDefaultImage(url_string):
  release = portal.portal_catalog.getResultValue(
    portal_type="Software Release",
    url_string=url_string,
  )
  if release is not None:
    software_product = release.getAggregateValue()
    return '%s/index_html' % software_product.getDefaultImageAbsoluteUrl()

  return ''

return CachingMethod(getCachedDefaultImage, 
     ('HostingSubscription_getDefaultImageAbsoluteUrl_cached',),
     cache_factory='erp5_ui_long')(subscription_item.getUrlString())
