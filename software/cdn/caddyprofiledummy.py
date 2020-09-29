class Recipe(object):
  def __init__(self, *args, **kwargs):
    pass

  def install(self):
    return []

  def update(self):
    return self.install()
