import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

import six

from slapos.recipe import simplelogger
from slapos.test.utils import makeRecipe


class TestSimpleLogger(unittest.TestCase):
  if six.PY2:
    assertRegex = unittest.TestCase.assertRegexpMatches

  def setUp(self):
    self.buildout_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.buildout_directory)

    self.wrapper_path = os.path.join(self.buildout_directory, 'logger')
    self.logfile = self.wrapper_path + '.log'
    self.recipe = makeRecipe(
        simplelogger.Recipe,
        options={
            'wrapper': self.wrapper_path,
            'log': self.logfile,
        },
        name='simplehttpserver',
    )

  def test_simple_logger(self):
    logger  = self.recipe.install()
    self.assertEqual(logger, self.wrapper_path)
    proc = subprocess.Popen(
        [logger],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate(input=b'test message line1\ntest message line2\n')
    self.assertFalse(out)

    with open(self.logfile) as f:
      content = f.read()
    self.assertRegex(
        content,
        re.compile(
          r'^\d{4}-\d{2}-\d{2}\.\d{2}:\d{2}\.\d{10}: test message line1\n'
          r'\d{4}-\d{2}-\d{2}\.\d{2}:\d{2}\.\d{10}: test message line2\n'
          r'\d{4}-\d{2}-\d{2}\.\d{2}:\d{2}\.\d{10}: ------------------------\n$'
        )
    )
