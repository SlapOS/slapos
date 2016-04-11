from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
integration_site = portal.restrictedTraverse(portal.portal_preferences.getPreferredPayzenIntegrationSite())

payzen_id = integration_site.getCategoryFromMapping('Causality/%s' % context.getId().replace('-', '_'))
if payzen_id != 'causality/%s' % context.getId().replace('-', '_'):
  date, payzen_id = payzen_id.split('_', 1)
  return DateTime(date).toZone('UTC'), payzen_id
else:
  return None, None
