import unittest

import os
import tempfile
import shutil

import runTestSuite

class TestWaitForSite(unittest.TestCase):
  test_result_filename = 'test_result.txt'
  def setUp(self):
    self.working_dir = tempfile.mkdtemp()
    self.partition_path = os.path.join(self.working_dir, 'partition0')
    self.test_script_result = os.path.join(self.working_dir,
        'partition1',
        'srv',
        'public',
        'test-script-result')
    os.makedirs(self.partition_path)
    os.makedirs(self.test_script_result)
    runTestSuite.SLEEP_TIME = 1
    runTestSuite.TRY_AMOUNT = 1
    
  def beforeTearDown(self):
    shutil.rmtree(self.working_dir)

  def createTestResultFile(self, result=''):
    open(os.path.join(
      self.test_script_result, self.test_result_filename), 'w').write(result)

  def test_empty_directory(self):
    result = runTestSuite.waitForSite(self.partition_path)
    self.assertEqual(result['command'], 'file not found')
    self.assertEqual(
      result['stdout'], 'Try 1/1: Test timed out and no result found.')
    self.assertFalse(result['success'])
    self.assertTrue('date' in result)
    self.assertTrue('duration' in result)
    self.assertFalse('stderr' in result)

  def test_empty_result(self):
    self.createTestResultFile()
    result = runTestSuite.waitForSite(self.partition_path)
    self.assertEqual(result['command'], os.path.join(
      self.test_script_result, self.test_result_filename))
    self.assertEqual(result['stdout'],
      'Try 1/1: Cannot find success nor failure result in the output\n'
      'Try 1/1: Time exceeded, success not found.')
    self.assertEqual(result['stderr'], 'Last result:\n')
    self.assertFalse(result['success'])
    self.assertTrue('date' in result)
    self.assertTrue('duration' in result)

  def test_unparsable_result(self):
    self.createTestResultFile('Unparsable result')
    result = runTestSuite.waitForSite(self.partition_path)
    self.assertEqual(result['command'], os.path.join(
      self.test_script_result, self.test_result_filename))
    self.assertEqual(result['stdout'],
      'Try 1/1: Cannot find success nor failure result in the output\n'
      'Try 1/1: Time exceeded, success not found.')
    self.assertEqual(result['stderr'], 'Last result:\nUnparsable result')
    self.assertFalse(result['success'])
    self.assertTrue('date' in result)
    self.assertTrue('duration' in result)

  def test_fatal_result(self):
    self.createTestResultFile(
      'FATAL: all hosts have already failed -- aborting')
    result = runTestSuite.waitForSite(self.partition_path)
    self.assertEqual(result['command'], os.path.join(
      self.test_script_result, self.test_result_filename))
    self.assertEqual(result['stdout'],
      'Try 1/1: Build not yet successful.\n'
      'Try 1/1: Time exceeded, success not found.')
    self.assertEqual(
      result['stderr'],
      'Last result:\nFATAL: all hosts have already failed -- aborting')
    self.assertFalse(result['success'])
    self.assertTrue('date' in result)
    self.assertTrue('duration' in result)

  def test_success_result(self):
    self.createTestResultFile(
      "\"msg\": \"[u'Build successful, connect to:', u'")
    result = runTestSuite.waitForSite(self.partition_path)
    print result
    self.assertEqual(result['command'], os.path.join(
      self.test_script_result, self.test_result_filename))
    self.assertEqual(result['stdout'], 'Try 1/1: Build successful.')
    self.assertEqual(
      result['stderr'],
      "Last result:\n\"msg\": \"[u'Build successful, connect to:', u'")
    self.assertTrue(result['success'])
    self.assertTrue('date' in result)
    self.assertTrue('duration' in result)
