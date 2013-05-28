#!/usr/bin/env python

import os
from datetime import datetime
from time import sleep
import gzip
import sys

class Reporter:
  def run(self, *args):
    json = self._aggregate(*args)
    if self._send(json):
      self._archive(path_list)
    else:
      self._fallback(*args)

  def _aggregate(self, paths):
    json = ""
    if paths:
      for path in paths:
        print ( path )
        with open(path, 'r') as f:
          json += f.read()
    return json

  # XXX : implement
  def _send(self, json_str):
    return False

  def _archive(self, paths, archive_dir):
    for path in paths:
      dirname = os.path.dirname(path)
      basename = os.path.basename(path)
      f = open(path, 'r')
      suffix = datetime.now() + '.gz'
      zipfile = gzip.open(archive_dir + basename + suffix, 'w')
      zipfile.writelines(f)
      os.remove(path)

  # XXX : set a more appropriate timer (like 1h or something)
  def _fallback(self, *args):
    sleep(30)
    self.run(*args)

def check(args):
  if not args:
    print('missing argument : filename list')
    sys.exit(-1)
  for arg in args:
    if not os.path.isfile(arg):
      print(arg + ' is not a valid path')
      sys.exit(-1)

if __name__  == '__main__':
  reporter = Reporter()
  # basically, we are waiting for a list of paths there
  args = sys.argv[1:]
  check(args)
  reporter.run(args)
