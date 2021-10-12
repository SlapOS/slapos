import os, shutil, tempfile, unittest
from slapos.recipe import promise_plugin
from slapos.test.utils import makeRecipe
from zc.buildout import UserError
from pprint import pformat
import stat, json
import six

class TestPromisePlugin(unittest.TestCase):

  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.output = os.path.join(self.tmp, 'output.py')
    self.options = {
      'output': self.output,
      'eggs': 'slapos.cookbook'
    }

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def makeRecipe(self):
    return makeRecipe(
            promise_plugin.Recipe,
            options=self.options,
            name='plugin')

  def installRecipe(self):
    self.makeRecipe().install()

  def setConfig(self):
    self.options['config-param1'] = "YY^@12"
    self.options['config-param2'] = "23'91'"
    self.options['config-param3'] = None
    self.options['config-param4'] = """param
in multi line
123444
"""

  def assertOutput(self, *expect):
    self.assertTrue(os.path.exists(self.output))
    with open(self.output, 'r') as f:
      content = f.read()
    for s in expect:
      self.assertIn(s, content)

  def assertConfig(self):
    items = self.options.items()
    expect = {k[7:] : v  for k, v in items if k.startswith('config-')}
    self.assertOutput("extra_config_dict = %s" % pformat(expect, indent=2))

  def assertEmptyConfig(self):
    self.assertOutput("extra_config_dict = %s" % ('{}' if six.PY3 else '{ }'))

  def test_module(self):
    self.options['module'] = 'slapos.promise.plugin.check_site_available'
    self.installRecipe()
    self.assertOutput("from %s import RunPromise" % self.options['module'])
    self.assertEmptyConfig()

  def test_file(self):
    self.options['file'] = __file__
    self.installRecipe()
    self.assertOutput("exec(_(%r))" % self.options['file'])
    self.assertEmptyConfig()

  def test_module_and_parameters(self):
    self.options['module'] = 'slapos.promise.plugin.check_site_available'
    self.setConfig()
    self.installRecipe()
    self.assertOutput("from %s import RunPromise" % self.options['module'])
    self.assertConfig()

  def test_file_and_parameters(self):
    self.options['file'] = __file__
    self.setConfig()
    self.installRecipe()
    self.assertOutput("exec(_(%r))" % self.options['file'])
    self.assertConfig()

  def test_mode(self):
    self.options['mode'] = '0644'
    self.options['module'] = 'slapos.promise.plugin.check_site_available'
    self.installRecipe()
    self.assertEqual(stat.S_IMODE(os.stat(self.output).st_mode), int('644', 8))

  def test_module_and_class(self):
    self.options['module'] = m = 'slapos.promise.plugin.check_site_available'
    self.options['class']  = 'MyPromise'
    self.installRecipe()
    self.assertOutput("from %s import MyPromise as RunPromise" % m)

  def test_file_and_class(self):
    self.options['file'] = __file__
    self.options['class'] = 'MyPromise'
    self.installRecipe()
    self.assertOutput("exec(_(%r))\n\nRunPromise = MyPromise" % __file__)

  def test_no_module_or_file(self):
    with self.assertRaises(UserError) as p:
      self.makeRecipe()
    msg = str(p.exception)
    self.assertEqual(msg, "Either 'module' or 'file' is required but not both")

  def test_module_and_file(self):
    self.options['module'] = 'slapos.promise.plugin.check_site_available'
    self.options['file'] = __file__
    self.test_no_module_or_file()

  def test_bad_parameters(self):
    self.options['module'] = 'slapos.promise.plugin.check_site_available'
    self.options.update((
      ('config-param1; print "toto"', '#xxxx"\nimport os; os.stat(f)'),
      ('config-param2\n@domething', '"#$$*PPP\np = 2*5; print "result=%s" % p')
    ))
    self.installRecipe()
    self.assertOutput(
      r"""'param1; print "toto"': '#xxxx"\nimport os; os.stat(f)',""",
      r"""'param2\n@domething': '"#$$*PPP\np = 2*5; print "result=%s" % p'"""
    )

  def test_bad_module(self):
    self.options['module'] = 'slapos.promise.plugin.check_site_available; print "toto"'
    with self.assertRaises(UserError) as p:
      self.makeRecipe()
    self.assertEqual(str(p.exception), "%r is not a valid module name" % self.options['module'])

  def test_bad_file(self):
    self.options['file'] = 'print "toto"'
    self.installRecipe()
    self.assertOutput(r"""exec(_('print "toto"'))""")

  def test_bad_class(self):
    self.options['class'] = 'MyPromise; print "toto"'
    with self.assertRaises(UserError) as p:
      self.makeRecipe()
    self.assertEqual(str(p.exception), "%r is not a valid class name" % self.options['class'])
