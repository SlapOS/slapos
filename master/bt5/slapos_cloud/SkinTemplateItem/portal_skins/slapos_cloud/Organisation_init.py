portal = context.getPortalObject()

reference = "SITE-%s" % portal.portal_ids.generateNewId(
    id_group='slap_organisation_reference',
    id_generator='uid')

context.edit(reference=reference)
