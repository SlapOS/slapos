portal_memcached = context
portal = context.getPortalObject()

# erp5-memcached-persistent is provided by SlapOS, so here we are
# ensuring the site uses real DNS Configuration provided by SlapOS.
# Port and name is hardcoded (unfortunally).
expected_url = "erp5-memcached-persistent:2003"

plugin = portal_memcached.restrictedTraverse("persistent_memcached_plugin", None)
if plugin is None:
  return ["portal_memcached/persistent_memcached_plugin wasn't found!"]

url = plugin.getUrlString()

if url != expected_url:
  fixing = ''
  if fixit:
    portal_memcached.persistent_memcached_plugin.edit(url_string=expected_url)
    fixing = ' (fixed)'

  return ["Kumofs not configured as expected%s: %s" %
    (fixing, "Expect %s\nGot %s" % (expected_url, url))]

return []
