from snapshot import Snapshot

class User(dict):
  def __init__(self, name, path):
    self.name = str(name)
    self.path = str(path)


  def dump(self, path):
    with open(path, 'a') as f:
      for v in self.values():
        if v.matters():
          f.write(v.__repr__() + "\n")

  def dumpSummary(self, path):
    summary = reduce(lambda x, y: x+y, self.values(), Snapshot(self.name))
    if summary.matters():
      with open(path, 'a') as f:
        f.write(summary.__repr__() + "\n")
