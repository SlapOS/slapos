if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

portal = context.getPortalObject()

network_portal_type = "Computer Network"

reference = "NET-%s" % portal.portal_ids.generateNewId(
    id_group='slap_network_reference',
    id_generator='uid')

module = portal.getDefaultModule(portal_type=network_portal_type)
network = module.newContent(
  portal_type=network_portal_type,
  title=title,
  reference=reference,
  source_administration=context.getRelativeUrl()
)


network.Base_redirect()
network.validate()
