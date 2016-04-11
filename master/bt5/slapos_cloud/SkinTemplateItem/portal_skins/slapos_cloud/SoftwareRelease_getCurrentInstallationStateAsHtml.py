from DateTime import DateTime
portal = context.getPortalObject()
import json

memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

error_style = 'background-color: red; display: block; height: 2em; width: 2em; float: left; margin: 5px;'
access_style = 'background-color: green; display: block; height: 2em; width: 2em; float: left; margin: 5px;'

software_installation = portal.portal_catalog.getResultValue(
                          portal_type='Software Installation',
                          validation_state='validated',
                          url_string=context.getUrlString(),
                          default_aggregate_uid=computer_uid
                        )
if not software_installation or software_installation.getSlapState() == "destroy_requested":
  return '<span" style="%s" title="Information not available"></a>' % error_style

try:
  d = memcached_dict[software_installation.getReference()]
except KeyError:
  return "<a href='%s' style='%s'></a>" % (software_installation.getRelativeUrl(),
                error_style)
else:
  d = json.loads(d)
  result = d['text']
  date = DateTime(d['created_at'])
  limit_date = DateTime() - 0.084
  if result.startswith('#error ') or (date - limit_date) < 0:
    access_style = error_style
    
  return "<a href='%s' style='%s' title='%s at %s'></a>" % (
              software_installation.getRelativeUrl(),
              access_style, result, d['created_at'])
