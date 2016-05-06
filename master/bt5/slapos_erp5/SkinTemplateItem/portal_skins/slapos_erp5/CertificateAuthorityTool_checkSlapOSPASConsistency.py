portal = context.getPortalObject()
slapos_plugin_dict = {
  'IExtractionPlugin': [
    'SlapOS Machine Authentication Plugin',
    'ERP5 Access Token Extraction Plugin',
  ],
  'IAuthenticationPlugin': [
    'SlapOS Machine Authentication Plugin',
    'SlapOS Shadow Authentication Plugin',
  ],
  'IGroupsPlugin': [
    'SlapOS Machine Authentication Plugin',
    'SlapOS Shadow Authentication Plugin',
  ],
  'IUserEnumerationPlugin': [
    'SlapOS Machine Authentication Plugin',
    'SlapOS Shadow Authentication Plugin',
  ]
}

def mergePASDictDifference(portal, d, fixit):
  plugins = portal.acl_users.plugins
  plugin_type_info = plugins.listPluginTypeInfo()
  error_list = []
  for plugin, active_list in d.iteritems():
    plugin_info = [q for q in plugin_type_info if q['id'] == plugin][0]
    found_list = plugins.listPlugins(plugin_info['interface'])
    meta_type_list = [q[1].meta_type for q in found_list]
    for expected in active_list:
      if expected not in meta_type_list:
        error = 'Plugin %s missing %s.' % (plugin, expected)
        if fixit:
          existing = [q for q in portal.acl_users.objectValues() if q.meta_type == expected]
          if len(existing) == 0:
            error_list.append('%s not found' % expected)
          else:
            plugins.activatePlugin(plugin_info['interface'], existing[0].getId())
            error += ' Fixed.'
        error_list.append(error)

  return error_list

pas_difference = mergePASDictDifference(portal, slapos_plugin_dict, fixit)
if len(pas_difference) != 0:

  message = "PAS not configured as expected"
  if fixit:
    message += ' (fixed). '
  else:
    message += ". "
  message += "Difference:\n%s" % ('\n'.join(pas_difference), )
  return [message]

return []
