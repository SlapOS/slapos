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
    self.assertEqual(buildout['urlinfo']['path'], 'search')
    self.assertEqual(buildout['urlinfo']['scheme'], 'http')
    self.assertEqual(buildout['urlinfo']['host'], 'www.google.com')
    self.assertEqual(buildout['urlinfo']['query'], 'hl=en&q=urlparse&btnG=Google+Search')

  def test_install(self):
    self.assertEqual(self.recipe.install(), [])
