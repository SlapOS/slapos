from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

portal = context.getPortalObject()
computer = context

reference = "TIOCONS-%s-%s" % (computer.getReference(), source_reference)
version = "%s" % context.getPortalObject().portal_ids.generateNewId(
  id_group=('slap_tioxml_consumption_reference', reference), default=1)

document = portal.consumption_document_module.newContent(
  portal_type="Computer Consumption TioXML File",
  source_reference=source_reference,
  title="%s consumption (%s)" % (computer.getReference(), source_reference),
  reference=reference,
  version=version,
  data=consumption_xml,
  classification="personal",
  publication_section="other",
  contributor_value=computer,
)
document.submit()
return document.getRelativeUrl()
