import urlparse

class Recipe(object):
  def __init__(self, *args, **kwargs):
    pass

  def install(self):
    return []

  def update(self):
    return self.install()

def validate_netloc(netloc):
  # a bit crazy way to validate that the passed parameter is haproxy
  # compatible server netloc
  parsed = urlparse.urlparse('scheme://'+netloc)
  if ':' in parsed.hostname:
    hostname = '[%s]' % parsed.hostname
  else:
    hostname = parsed.hostname
  return netloc == '%s:%s' % (hostname, parsed.port)
