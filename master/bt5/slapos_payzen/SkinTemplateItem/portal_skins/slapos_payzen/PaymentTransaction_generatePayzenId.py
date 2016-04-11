from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
integration_site = portal.restrictedTraverse(portal.portal_preferences.getPreferredPayzenIntegrationSite())

transaction_date, transaction_id = context.PaymentTransaction_getPayzenId()
if transaction_id is not None:
  # XXX raise?
  return None, None

now = DateTime().toZone('UTC')
today = now.asdatetime().strftime('%Y%m%d')

transaction_id = str(portal.portal_ids.generateNewId(
  id_group='%s_%s' % (integration_site.getRelativeUrl(), today),
  id_generator='uid')).zfill(6)

mapping_id = '%s_%s' % (today, transaction_id)
# integration_site.Causality[mapping_id].setDestinationReference(context.getRelativeUrl())
# try:
#   integration_site.getCategoryFromMapping('Causality/%s' % mapping_id, create_mapping_line=True, create_mapping=True)
# except ValueError:
#   mapping = integration_site.Causality[mapping_id]
#   mapping.setDestinationReference('%s' % context.getRelativeUrl())
# else:
#   raise ValueError, "Payzen transaction_id already exists"

try:
  mapping = integration_site.getCategoryFromMapping(
  'Causality/%s' % context.getId().replace('-', '_'),
  create_mapping_line=True,
  create_mapping=True)
except ValueError:
  pass
integration_site.Causality[context.getId().replace('-', '_')].setDestinationReference(mapping_id)

return context.PaymentTransaction_getPayzenId()
