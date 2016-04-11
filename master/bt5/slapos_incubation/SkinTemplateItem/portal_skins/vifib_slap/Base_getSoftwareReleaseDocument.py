# try to find, if needed create and publish
portal = context.getPortalObject()
software_release_document = portal.portal_catalog.getResultValue(portal_type='Software Release',
  url_string=software_release_url)
if software_release_document is None:
  digest = context.Base_getSha512Hexdiest(software_release_url)
  tag = '%s_inProgress' % digest
  if portal.portal_activities.countMessageWithTag(tag) == 0:
    # can create new one
    software_release_document = portal.software_release_module.newContent(
      portal_type='Software Release',
      reference=digest,
      version=digest,
      url_string=software_release_url,
      language='en',
      activate_kw={'tag': tag}
    )
    software_release_document.publish(comment='Automatically created.')
return software_release_document
