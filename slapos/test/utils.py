"""Test helpers
"""
import sys
import os.path
from zc.buildout.configparser import parse

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
  # in SLAPOS-EGG-TEST the usual layout is
  # ${buildout:directory}/parts/slapos-repository/slapos/test/utils.py in instance buildout, so try
  # to find a buildout.cfg relative to this file.
  # What can also happens is that this repository is used from software folder, this is the case in
  # SLAPOS-SR-TEST. In this case, ${buildout:eggs} is not set in buildout.cfg and we can only assume
  # it will be the standards eggs and develop-eggs folders.

  # {BASE_DIRECTORY}/parts/slapos-repository/slapos/test/utils.py
  base_directory = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
  buildout_cfg = os.path.join(base_directory, 'buildout.cfg')

  if os.path.exists(buildout_cfg):
    with open(buildout_cfg) as f:
      parsed_cfg = parse(f, buildout_cfg)

    # When buildout_cfg is an instance buildout (like in SLAPOS-EGG-TEST),
    # there's a ${buildout:eggs-directory} we can use.
    # When buildout_cfg is a software buildout, we can only guess the
    # standard eggs directories.
    eggs_directory = parsed_cfg['buildout'].get(
      'eggs-directory', os.path.join(base_directory, 'eggs'))
    develop_eggs_directory = parsed_cfg['buildout'].get(
      'develop-eggs-directory', os.path.join(base_directory, 'develop-eggs'))

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

