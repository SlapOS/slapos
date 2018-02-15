portal = context.getPortalObject()
acl_users = portal.acl_users
plugin_id = 'slapos_machine'
error_list = []
if plugin_id not in acl_users.plugins.getAllPlugins(plugin_type='IExtractionPlugin')['active']:
  error_list.append('SlapOS Machine Authentication Plugin is desactive as %s/%s' % (acl_users.getPath(), plugin_id))
  if fixit:
    tag = 'slapos_login_migration'
    portal.portal_catalog.activate(tag=tag, activity='SQLQueue').searchAndActivate(
      portal_type=('Computer', 'Software Instance'),
      activate_kw={'tag': tag, 'priority': 6},
      method_id='Instance_migrateToERP5Login',
    )
    getattr(acl_users, plugin_id).manage_activateInterfaces([
      'IExtractionPlugin'
    ])
return error_list
