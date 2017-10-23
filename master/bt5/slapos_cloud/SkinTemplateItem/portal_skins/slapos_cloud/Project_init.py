portal = context.getPortalObject()

reference = "PROJ-%s" % portal.portal_ids.generateNewId(
    id_group='slap_project_reference',
    id_generator='uid', default=1)

context.edit(codification=reference,
             reference=reference)

# project.validate()
