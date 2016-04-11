portal = context.getPortalObject()
portal.portal_catalog.searchAndActivate(
  portal_type='Software Product',
  validation_state='published',
  method_id='SoftwareProduct_manageSoftwareCatalog',
  activate_kw={'tag': tag}
)

context.activate(after_tag=tag).getId()
