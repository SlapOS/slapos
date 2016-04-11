from Products.CMFActivity.ActiveResult import ActiveResult

portal = context.getPortalObject()
def mergePASDictDifference(portal, d, fixit):
  plugins = portal.acl_users.plugins
  error_list = []
  plugin_type_info = plugins.listPluginTypeInfo()
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

pas_difference = mergePASDictDifference(portal, promise_dict, fixit)
if len(pas_difference) != 0:
  if fixit:
    severity = 0
  else:
    severity = 1
  summary = "PAS not configured as expected"
  if fixit:
    summary += ' (fixed)'
  detail = "Difference:\n%s" % ('\n'.join(pas_difference), )
else:
  severity = 0
  summary = "Nothing to do."
  detail = ""

active_result = ActiveResult()
active_result.edit(
  summary=summary, 
  severity=severity,
  detail=detail)

context.newActiveProcess().postResult(active_result)
