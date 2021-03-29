"""Test helpers
"""
import os
import sys


def makeRecipe(recipe_class, options, name='test', slap_connection=None):
  """Instanciate a recipe of `recipe_class` with `options` with a buildout
  mapping containing a python and an empty `slapos-connection` mapping, unless
  provided as `slap_connection`.

  This function expects the test suite to have set SLAPOS_TEST_EGGS_DIRECTORY
  and SLAPOS_TEST_DEVELOP_EGGS_DIRECTORY environment variables, so that the
  test recipe does not need to install eggs again when using working set.
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

  buildout['buildout']['eggs-directory'] = os.environ['SLAPOS_TEST_EGGS_DIRECTORY']
  buildout['buildout']['develop-eggs-directory'] = os.environ['SLAPOS_TEST_DEVELOP_EGGS_DIRECTORY']

  # Prevent test from accidentally writing to the buildout's eggs
  buildout['buildout']['newest'] = False
  buildout['buildout']['offline'] = True

  return recipe_class(buildout=buildout, name=name, options=options)

