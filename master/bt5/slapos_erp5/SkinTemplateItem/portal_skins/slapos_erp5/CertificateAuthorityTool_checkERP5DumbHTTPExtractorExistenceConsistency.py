acl_users = context.getPortalObject().acl_users
plugin_id = 'erp5_dumb_http_extraction'
error_list = []
if plugin_id not in acl_users.objectIds():
  error_list.append('ERP5 Dumb HTTP Extraction Plugin does not exist as %s/%s' % (acl_users.getPath(), plugin_id))
  if fixit:
    acl_users.manage_addProduct['ERP5Security'].addERP5DumbHTTPExtractionPlugin(plugin_id)
    getattr(acl_users, plugin_id).manage_activateInterfaces([
      'IExtractionPlugin'
    ])
return error_list
