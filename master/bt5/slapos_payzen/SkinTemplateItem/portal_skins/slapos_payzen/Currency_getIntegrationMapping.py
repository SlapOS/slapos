portal = context.getPortalObject()
integration_site = portal.restrictedTraverse(portal.portal_preferences.getPreferredPayzenIntegrationSite())

relative_url = context.getRelativeUrl()
# Only EUR is supported for now
assert relative_url == 'currency_module/EUR'
return integration_site.getMappingFromCategory('resource/%s' % relative_url).split('/', 1)[-1]
