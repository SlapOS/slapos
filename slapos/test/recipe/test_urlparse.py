import unittest
import zc.buildout.testing

class UrlparseTest(unittest.TestCase):
  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    buildout['urlinfo'] = {}
    buildout['urlinfo']['url'] = "http://www.google.com/search?hl=en&q=urlparse&btnG=Google+Search"
    from slapos.recipe import _urlparse
    self.recipe = _urlparse.Recipe(buildout,"urlinfo",buildout['urlinfo'])

  def test_options(self):
    buildout = self.buildout
    self.assertTrue(buildout['urlinfo'])
    self.assertTrue(buildout['urlinfo']['path'])
    self.assertTrue(buildout['urlinfo']['scheme'])
    self.assertTrue(buildout['urlinfo']['host'])
    self.assertTrue(buildout['urlinfo']['query'])

  def test_install(self):
    self.assertEqual(self.recipe.install(), [])