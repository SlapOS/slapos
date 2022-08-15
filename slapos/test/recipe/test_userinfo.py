import unittest
import zc.buildout.testing

class UserInfoTest(unittest.TestCase):
  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    buildout['userinfo'] = {}
    from slapos.recipe import userinfo
    self.recipe = userinfo.Recipe(
        buildout,
        'userinfo',
        buildout['userinfo'])

  def test_options(self):
    buildout = self.buildout
    self.assertTrue(buildout['userinfo']['pw-name'])
    self.assertTrue(buildout['userinfo']['pw-uid'])
    self.assertTrue(buildout['userinfo']['pw-gid'])
    self.assertTrue(buildout['userinfo']['pw-dir'])
    self.assertTrue(buildout['userinfo']['pw-shell'])

    self.assertTrue(buildout['userinfo']['gr-name'])
    self.assertTrue(buildout['userinfo']['gr-gid'])

  def test_install(self):
    self.assertEqual(self.recipe.install(), [])
