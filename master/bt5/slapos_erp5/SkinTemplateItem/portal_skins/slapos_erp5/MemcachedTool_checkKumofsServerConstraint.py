portal_memcached = context
portal = context.getPortalObject()
promise_url = portal.getPromiseParameter('external_service', 'kumofs_url')

if promise_url is None:
  return

plugin = portal_memcached.restrictedTraverse("persistent_memcached_plugin", None)
if plugin is None:
  return []

url = "memcached://%s/" % plugin.getUrlString()

if promise_url != url:
  fixing = ''
  if fixit:
    _, promise_url = promise_url.split('://', 1)

    domain_port = promise_url.split('/', 1)[0]
    port = domain_port.split(':')[-1]
    domain = domain_port[:-(len(port)+1)]
    
    portal_memcached.persistent_memcached_plugin.edit(url_string="%s:%s" % (domain, port))
    fixing = ' (fixed)'

  return ["Kumofs not configured as expected%s: %s" %
    (fixing, "Expect %s\nGot %s" % (promise_url, url))]

return []
