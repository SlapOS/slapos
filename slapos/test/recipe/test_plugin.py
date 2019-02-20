import os, shutil, tempfile, unittest
from slapos.recipe import promise_plugin
from slapos.test.utils import makeRecipe
import stat, json

class TestPromisePlugin(unittest.TestCase):

  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.output = os.path.join(self.tmp, 'output.py')
    self.options = options = {
      'output': self.output,
      'eggs': 'slapos.cookbook'
    }

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def test_parameters(self):
    self.options['mode'] = '0644'
    self.options['import'] = 'slapos.promise.plugin.check_site_available'
    self.options['config-param1'] = "YY^@12"
    self.options['config-param2'] = "23'91'"
    self.options['config-param3'] = None
    self.options['config-param4'] = """param
in multi line
123444
"""
    recipe = makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')
    recipe.install()

    self.assertTrue(os.path.exists(self.output))
    with open(self.output) as f:
      content = f.read()
    self.assertIn("from slapos.promise.plugin.check_site_available import RunPromise", content)
    self.assertEqual(stat.S_IMODE(os.stat(self.output).st_mode), int('644', 8))

    expected_dict = dict(
      param1=self.options['config-param1'],
      param2=self.options['config-param2'],
      param3=self.options['config-param3'],
      param4=self.options['config-param4'],
    )
    self.assertIn('extra_config_dict = json.loads("""%s""", strict=False)' % json.dumps(expected_dict, indent=2, sort_keys=True), content)

  def test_no_module_set(self):
    recipe = makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')
    with self.assertRaises(KeyError):
      recipe.install()

  def test_default(self):
    self.options['import'] = 'slapos.promise.plugin.check_site_available'
    recipe = makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')
    recipe.install()

    self.assertTrue(os.path.exists(self.output))
    self.assertEqual(stat.S_IMODE(os.stat(self.output).st_mode), int('644', 8))
    with open(self.output) as f:
      content = f.read()
    self.assertIn("from slapos.promise.plugin.check_site_available import RunPromise", content)
    self.assertIn('extra_config_dict = json.loads("""{}""", strict=False)', content)


  def test_bad_parameters(self):
    self.options['import'] = 'slapos.promise.plugin.check_site_available'
    self.options['config-param1; print "toto"'] = """#xxxx"\nimport os; os.stat(f)"""
    self.options['config-param2\n@domething'] = '"#$$*PPP\n\n p = 2*5; print "result is %s" % p'
    recipe = makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')
    recipe.install()

    self.assertTrue(os.path.exists(self.output))
    with open(self.output) as f:
      content = f.read()

    expected_param1 = '"param1; print \\"toto\\"": "#xxxx\\"\\nimport os; os.stat(f)",'
    expected_param2 = '"param2\\n@domething": "\\"#$$*PPP\\n\\n p = 2*5; print \\"result is %s\\" % p"'
    self.assertIn(expected_param1, content)
    self.assertIn(expected_param2, content)

  def test_bad_module_path(self):
    self.options['import'] = 'slapos.promise.plugin.check_site_available; print "toto"'
    recipe = makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')
    with self.assertRaises(ValueError) as p:
      recipe.install()

    self.assertEqual(p.exception.message, "Import path %r is not a valid" % self.options['import'])

  def test_bad_content(self):
    self.options['content'] = 'from slapos.plugin.check_site_available import toto; print "toto"'
    recipe = makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')
    with self.assertRaises(ValueError) as p:
      recipe.install()

    self.assertEqual(p.exception.message, "Promise content %r is not valid" % self.options['content'])

