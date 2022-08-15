import os
import shutil
import tempfile
import unittest

import zc.buildout.testing

from slapos.recipe import zero_knowledge


class ZeroKnowledgeTest(unittest.TestCase):
  def setUp(self):
    self.tmp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp_dir)

    self.buildout = zc.buildout.testing.Buildout()
    self.buildout['buildout']['directory'] = self.tmp_dir

  def test_write_read(self):
    buildout = self.buildout
    buildout['zero-knowledge-write'] = {
        'filename': 'zero-knowledge.cfg',
        'recipe': 'slapos.cookbook:zero-knowledge.read',
        'secret': '?',
    }
    buildout['zero-knowledge-read'] = {
        'filename': 'zero-knowledge.cfg',
        'recipe': 'slapos.cookbook:zero-knowledge.read',
    }

    write_recipe = zero_knowledge.WriteRecipe(
        buildout,
        'zero-knowledge-write',
        buildout['zero-knowledge-write'],
    )
    write_recipe.install()
    self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, 'zero-knowledge.cfg',)))

    zero_knowledge.ReadRecipe(
        buildout,
        'zero-knowledge-read',
        buildout['zero-knowledge-read'],
    )
  
    self.assertEqual(buildout['zero-knowledge-read']['secret'], '?')
