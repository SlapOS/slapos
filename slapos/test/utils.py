"""Test helpers
"""
import sys
import os.path
from ConfigParser import ConfigParser

import logging

def makeRecipe(recipe_class, options, name='test', slap_connection=None):
  """Instanciate a recipe of `recipe_class` with `options` with a buildout
  mapping containing a python and an empty `slapos-connection` mapping, unless
  provided as `slap_connection`.

  If running tests in a buildout folder, the test recipe will reuse the
  `eggs-directory` and `develop-eggs-directory` from this buildout so that the
  test recipe does not need to install eggs again when using working set.
  To prevent test accidentally writing to the buildout's eggs repositories, we
  set `newest` to false and `offline` to true in this case.
  """
  buildout = {
    'buildout': {
      'bin-directory': '',
      'find-links': '',
      'allow-hosts': '',
      'develop-eggs-directory': '',
      'eggs-directory': '',
      'python': 'testpython',
    },
    'testpython': {
      'executable': sys.executable,
    },
    'slap-connection': {
       'computer-id': '',
       'partition-id': '',
       'server-url': '',
       'software-release-url': '',
     }
  }
  if slap_connection is not None:
    buildout['slap-connection'] = slap_connection

  # are we in buildout folder ?
  # the usual layout is
  # ${buildout:directory}/parts/slapos-repository/slapos/test/utils.py , so try
  # to find a buildout relative to this file.
  buildout_cfg = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'buildout.cfg')
  if os.path.exists(buildout_cfg):
    parser = ConfigParser()
    parser.readfp(open(buildout_cfg))
    eggs_directory = parser.get('buildout', 'eggs-directory')
    develop_eggs_directory = parser.get('buildout', 'develop-eggs-directory')
    logging.getLogger(__name__).info(
        'Using eggs-directory (%s) and develop-eggs-directory (%s) from buildout at %s',
        eggs_directory,
        develop_eggs_directory,
        buildout_cfg)
    buildout['buildout']['eggs-directory'] = eggs_directory
    buildout['buildout']['develop-eggs-directory'] = develop_eggs_directory
    buildout['buildout']['newest'] = False
    buildout['buildout']['offline'] = True
  return recipe_class(buildout=buildout, name=name, options=options)

