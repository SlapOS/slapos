
# import fnmatch
import os
import shutil
# import pprint

def post_make_hook(options, buildout):
  location = options['location']
  print "Mioga - postmakehook"
  print "We are currently in", os.getcwd()
  shutil.move("var", location)
