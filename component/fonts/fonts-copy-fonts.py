import os
import textwrap
import glob
import shutil

def post_make_hook(options, buildout, environment=None):
  prefix = options['prefix']
  for name, location in (line.split() for line in options['fonts'].splitlines()):
    shutil.copytree(location, os.path.join(prefix, name))
