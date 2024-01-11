import os
import subprocess
import tempfile
import unittest

import zc.buildout.testing

from slapos.recipe import check_parameter


class TestCheckParameter(unittest.TestCase):
  def setUp(self):
    self.buildout = zc.buildout.testing.Buildout()

  def _makeRecipe(self, options):
    path = tempfile.NamedTemporaryFile(delete=False).name
    self.addCleanup(os.unlink, path)
    options.setdefault("path", path)
    self.buildout["check-parameter"] = options

    recipe = check_parameter.Recipe(
      self.buildout, "check-parameter", self.buildout["check-parameter"]
    )
    return recipe

  def test_expected_value_ok(self):
    script = self._makeRecipe({"expected-value": "foo", "value": "foo"}).install()
    subprocess.check_call(script)

  def test_expected_value_not_ok(self):
    script = self._makeRecipe({"expected-value": "foo", "value": "bar"}).install()
    with self.assertRaises(subprocess.CalledProcessError) as e:
      subprocess.check_output(script, universal_newlines=True)
    self.assertEqual(e.exception.output, "FAIL: bar != foo\n")

  def test_expected_value_multi_lines_ok(self):
    script = self._makeRecipe(
      {"expected-value": "foo\nbar", "value": "foo\nbar"}
    ).install()
    subprocess.check_output(script)

  def test_expected_value_multi_lines_not_ok(self):
    script = self._makeRecipe({"expected-value": "foo\nbar", "value": "foo"}).install()
    with self.assertRaises(subprocess.CalledProcessError) as e:
      subprocess.check_output(script, universal_newlines=True)
    self.assertEqual(e.exception.output, "FAIL: foo != foo\nbar\n")

  def test_expected_not_value_ok(self):
    script = self._makeRecipe({"expected-not-value": "foo", "value": "bar"}).install()
    subprocess.check_call(script)

  def test_expected_not_value_not_ok(self):
    script = self._makeRecipe({"expected-not-value": "foo", "value": "foo"}).install()
    with self.assertRaises(subprocess.CalledProcessError) as e:
      subprocess.check_output(script, universal_newlines=True)
    self.assertEqual(e.exception.output, "FAIL: foo == foo\n")
