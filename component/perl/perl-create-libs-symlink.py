
import fnmatch
import os
import pprint


def post_make_hook(options, buildout):
  location = options['location']
  matches = []
  for root, dirnames, filenames in os.walk(location):
    for filename in fnmatch.filter(filenames, 'libperl.a'):
      matches.append(os.path.join(root, filename))
  nr_matches = len(matches)
  if nr_matches == 0:
    print "ERROR - no libperl.* found!"
    exit
  elif nr_matches > 1:
    print "WARNING - several libperl.a found, taking only the first one:", "\n".join(matches)
  
  # matches[0] is a prefix of "location"
  # For the symlink, we want the relative path.
  rel_link = os.path.relpath(os.path.dirname(matches[0]), location)
  simlink_location = os.path.join(location, "libs-c")
  if os.path.islink(simlink_location):
    os.unlink(simlink_location)
  os.symlink(rel_link, simlink_location)
  print "Created symlink \"libs-c\" to", rel_link
