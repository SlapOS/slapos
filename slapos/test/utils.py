"""Test helpers
"""
import os
import sys
import six


def makeRecipe(recipe_class, options, name='test', buildout=None):
  """Instantiate a recipe of `recipe_class` with `options` with a `buildout`
  mapping containing by default a python and an empty slap-connection.

  This function expects the test suite to have set SLAPOS_TEST_EGGS_DIRECTORY
  and SLAPOS_TEST_DEVELOP_EGGS_DIRECTORY environment variables, so that the
  test recipe does not need to install eggs again when using working set.
  """
  _buildout = six.moves.UserDict({
    'buildout': {
      'bin-directory': '',
      'find-links': '',
      'allow-hosts': '',
      'allow-unknown-extras': False,
      'develop-eggs-directory': '',
      'eggs-directory': '',
      'directory': '',
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
  })

  _buildout['buildout']['eggs-directory'] = os.environ['SLAPOS_TEST_EGGS_DIRECTORY']
  _buildout['buildout']['develop-eggs-directory'] = os.environ['SLAPOS_TEST_DEVELOP_EGGS_DIRECTORY']

  if buildout:
    for section, _options in six.iteritems(buildout):
      _buildout.setdefault(section, {}).update(**_options)

  # Prevent test from accidentally writing to the buildout's eggs
  _buildout['buildout']['newest'] = False
  _buildout['buildout']['offline'] = True

  return recipe_class(buildout=_buildout, name=name, options=options)

