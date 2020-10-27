import json

class Recipe(object):
  def __init__(self, *args, **kwargs):
    pass

  def install(self):
    return []

  def update(self):
    return self.install()

class CdnSlaveParse(object):
  def __init__(self, buildout, name, options):
    self.options = options

  def install(self):
    output = self.options['output']
    with open(output, 'w') as fh:
      json.dump(self.options['slave-information'], fh, indent=2)
    return [output]

  def update(self):
    # nothing to do during update
    return []
