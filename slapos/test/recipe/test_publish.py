import os
import shutil
import tempfile
import time
import unittest

try:
  import subprocess32 as subprocess
except ImportError:
  import subprocess

import zc.buildout.testing


class PublishTest(unittest.TestCase):
  ipv4 = os.environ['SLAPOS_TEST_IPV4']
  ipv6 = os.environ['SLAPOS_TEST_IPV6']
  port = 5432

  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    buildout['publish'] = {}
    buildout['slap-connection'] = {
      'computer-id': '',
      'partition-id': '',
      'server-url': '',
      'software-release-url': '',
    }
    from slapos.recipe import publish
    self.recipe = publish.Recipe(
        buildout,
        'publish',
        buildout['publish'])

  def test_options(self):
    self.assertEqual(
        self.buildout['publish'],
        {}
    )

  def test_install(self):
    installed = self.recipe.install()
