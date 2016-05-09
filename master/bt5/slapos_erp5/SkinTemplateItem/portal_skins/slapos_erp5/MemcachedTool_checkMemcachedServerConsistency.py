portal_memcached = context

portal = context.getPortalObject()
promise_url = portal.getPromiseParameter('external_service', 'memcached_url')

if promise_url is None:
  return

plugin = portal_memcached.default_memcached_plugin

url = "memcached://%s/" % plugin.getUrlString()

if promise_url != url:
  fixing = ''
  if fixit:
    fixing = ' (fixed)'
    _, promise_url = promise_url.split('://', 1)

    domain_port = promise_url.split('/', 1)[0]
    port = domain_port.split(':')[-1]
    domain = domain_port[:-(len(port)+1)]

    portal_memcached.default_memcached_plugin.edit(url_string="%s:%s" % (domain, port))
  return ["Memcached not configured as expected%s: %s" %
    (fixing, "Expect %s\nGot %s" % (promise_url, url))]
else:
  return []
