integration_site = context.getPortalObject().restrictedTraverse(
    'portal_integrations/slapos_aggregated_delivery_integration_site')


person_id = context.getId().replace('-', '_')
integration_site.Causality[person_id].setDestinationReference(delivery.getRelativeUrl())
