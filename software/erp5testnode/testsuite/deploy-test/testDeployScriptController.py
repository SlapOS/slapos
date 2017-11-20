import unittest

import os
import shutil
import subprocess
import tempfile

class TestDeployScriptController(unittest.TestCase):
  deployment_script = """#!/bin/bash
echo "This is deployment script"
exit 0
"""

  def createMockExecutable(self, name, content):
    fname = os.path.join(self.mock_dir, name)
    with open(fname, 'w') as fd:
      fd.write(content)
    os.chmod(fname, 0o755)

  def prepareMockDir(self):
    self.createMockExecutable('wget', """#!/bin/bash
if [ "$4" == "http://10.0.2.100/data" ] ; then
  cat > $2 <<EOF
URL=http://fake/fake
WAITTIME=1
TRIES=1
EOF
elif [ "$4" == "http://fake/fake" ] ; then
  cat > $2 <<EOF
%s
EOF
  echo "no data"
fi
""" % self.deployment_script)
    self.createMockExecutable('curl', """#!/bin/bash
echo $7 | cut -d @ -f 2 > $0.result
""")

  def setUp(self):
    self.working_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(self.working_dir, 'tmp'))
    os.makedirs(os.path.join(self.working_dir, 'var', 'log'))
    slapos_log_dir = os.path.join(self.working_dir, 'opt', 'slapos', 'log')
    os.makedirs(slapos_log_dir)
    open(os.path.join(slapos_log_dir, 'slapos-node-software.log'), 'w').write(
      'This is software log\n'  
    )
    open(os.path.join(slapos_log_dir, 'slapos-node-instance.log'), 'w').write(
      'This is instance log\n'  
    )
    self.mock_dir = tempfile.mkdtemp()

  def beforeTearDown(self):
    shutil.rmtree(self.working_dir)
    shutil.rmtree(self.mock_dir)

  def runDeployScriptController(self):
    code = subprocess.call(
      ['/bin/bash', 'deploy-script-controller'], env=dict(
        TEST_PREFIX=self.working_dir,
        PATH=self.mock_dir + ':' + os.environ['PATH'])
    )
    return code, open(
      open(os.path.join(self.mock_dir, 'curl.result')).read().strip()).read()

  def test(self):
    self.prepareMockDir()
    code, result = self.runDeployScriptController()
    self.assertEqual(0, code)
    self.assertTrue('This is deployment script' in result)
    self.assertTrue('This is software log' in result)
    self.assertTrue('This is instance log' in result)
    self.assertTrue(
      'deploy-script-controller: Try 1. Script executed successfully.' in result)

  def test_failing(self):
    self.deployment_script = """#!/bin/bash
echo "This is failing deployment script"
exit 1
"""
    self.prepareMockDir()
    code, result = self.runDeployScriptController()
    self.assertEqual(1, code)
    self.assertTrue('This is failing deployment script' in result)
    self.assertTrue('This is software log' in result)
    self.assertTrue('This is instance log' in result)
    self.assertTrue(
      'deploy-script-controller: Try 2. Amount of tries 1 exceeded, giving up.' in result)
