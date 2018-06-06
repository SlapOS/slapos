# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2018 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import os, shutil
import tempfile
import unittest
import sys
import time
import json
import random
import logging
from datetime import datetime, timedelta
import Queue
from zope import interface as zope_interface
from slapos.grid.promise import interface, PromiseLauncher, PromiseProcess, PromiseError
from slapos.grid.promise.generic import (GenericPromise, TestResult, AnomalyResult,
                                         PromiseQueueResult, PROMISE_STATE_FOLDER_NAME,
                                         PROMISE_RESULT_FOLDER_NAME,
                                         PROMISE_PARAMETER_NAME)

class TestSlapOSPromiseMixin(unittest.TestCase):

  def setUp(self):
    self.partition_dir = tempfile.mkdtemp()
    self.plugin_dir = os.path.join(self.partition_dir, 'plugins')
    self.legacy_promise_dir = os.path.join(self.partition_dir, 'promise')
    self.log_dir = os.path.join(self.partition_dir, 'log')
    os.mkdir(self.plugin_dir)
    os.mkdir(self.log_dir)
    os.makedirs('%s/.slapgrid/promise' % self.partition_dir)
    os.mkdir(self.legacy_promise_dir)
    self.partition_id = "slappart0"
    self.computer_id = "COMP-1234"

  def writeInit(self):
    with open(os.path.join(self.plugin_dir, '__init__'), 'w') as f:
      f.write('')
    os.chmod(os.path.join(self.plugin_dir, '__init__'), 0644)
    if sys.path[0] != self.plugin_dir:
      sys.path[0:0] = [self.plugin_dir]

  def tearDown(self):
    if os.path.exists(self.partition_dir):
      shutil.rmtree(self.partition_dir)
    if sys.path[0] == self.plugin_dir:
      del sys.path[0]

  def configureLauncher(self, save_method=None, timeout=1, master_url="", debug=False,
      run_list=[], uid=None, gid=None, enable_anomaly=False, force=False,
      logdir=True, dry_run=False):
    parameter_dict = {
      'promise-timeout': timeout,
      'promise-folder': self.plugin_dir,
      'legacy-promise-folder': self.legacy_promise_dir,
      'log-folder': self.log_dir if logdir else None,
      'partition-folder': self.partition_dir,
      'master-url': master_url,
      'partition-cert': "",
      'partition-key': "",
      'partition-id': self.partition_id,
      'computer-id': self.computer_id,
      'debug': debug,
      'check-anomaly': enable_anomaly,
      'force': force,
      'run-only-promise-list': run_list,
      'uid': uid,
      'gid': gid
    }

    self.launcher = PromiseLauncher(
      config=parameter_dict,
      logger=None,
      dry_run=dry_run
    )
    if save_method:
      self.launcher._savePromiseResult = save_method

  def genPromiseConfigDict(self, promise_name):
    return {
      'log-folder': None,
      'partition-folder': self.partition_dir,
      'master-url': "https://master.url.com",
      'partition-cert': "",
      'partition-key': "",
      'partition-id': self.partition_id,
      'computer-id': self.computer_id,
      'debug': False,
      'name': promise_name,
      'path': os.path.join(self.plugin_dir, promise_name),
      'queue': Queue.Queue(),
    }

  def createPromiseProcess(self, promise_name, check_anomaly=False, wrap=False):

    logging.basicConfig()
    promise_path = os.path.join(self.plugin_dir, promise_name)
    return PromiseProcess(
      self.partition_dir,
      promise_name,
      promise_path,
      logger=logging.getLogger('grid.promise'),
      argument_dict=self.genPromiseConfigDict(promise_name),
      check_anomaly=check_anomaly,
      wrap=wrap,
    )

  def writeFile(self, path, content, mode=0644):
    with open(path, 'w') as f:
      f.write(content)
    os.chmod(path, mode)

  def generatePromiseScript(self, name, success=True, failure_count=1, content="",
    periodicity=0.03):
    promise_content = """from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise import GenericPromise

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    self.setPeriodicity(minute=%(periodicity)s)

  def sense(self):
    %(content)s

    if not %(success)s:
      self.logger.error("failed")
    else:
      self.logger.info("success")

  def anomaly(self):
    return self._anomaly(latest_minute=%(periodicity)s, failure_amount=%(failure_amount)s)

  def test(self):
    return self._test(latest_minute=%(periodicity)s, failure_amount=%(failure_amount)s)

""" % {'success': success, 'content': content, 'failure_amount': failure_count,
       'periodicity': periodicity}

    with open(os.path.join(self.plugin_dir, name), 'w') as f:
      f.write(promise_content)


class TestSlapOSPromiseLauncher(TestSlapOSPromiseMixin):

  def test_promise_match_interface(self):
    promise_name = 'my_promise.py'
    self.writeInit()
    self.generatePromiseScript(promise_name)
    promise_process = self.createPromiseProcess(promise_name)

    promise_module = promise_process._loadPromiseModule()

  def test_promise_match_interface_bad_name(self):
    promise_name = 'my_promise_no_py'
    self.writeInit()
    self.generatePromiseScript(promise_name)
    promise_process = self.createPromiseProcess(promise_name)

    with self.assertRaises(ImportError) as exc:
      promise_module = promise_process._loadPromiseModule()
    self.assertEquals(exc.exception.message, 'No module named my_promise_no_py')

  def test_promise_match_interface_no_implement(self):
    promise_name = 'my_promise_noimplement.py'
    promise_content = """from slapos.grid.promise import GenericPromise

class RunPromise(GenericPromise):

  def __init__(self, config):
    GenericPromise.__init__(self, config)

  def sense(self):
    pass
    
"""
    promise_path = os.path.join(self.plugin_dir, promise_name)
    self.writeFile(promise_path, promise_content)
    self.writeInit()
    promise_process = self.createPromiseProcess(promise_name)

    with self.assertRaises(RuntimeError) as exc:
      promise_module = promise_process._loadPromiseModule()
    message = "RunPromise class in my_promise_noimplement.py must implements" \
      " 'IPromise' interface. zope_interface.implements(interface.IPromise) is missing ?"
    self.assertEquals(exc.exception.message, message)

  def test_promise_match_interface_no_generic(self):
    promise_name = 'my_promise_nogeneric.py'
    promise_content = """from zope import interface as zope_interface
from slapos.grid.promise import interface

class RunPromise(object):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    pass

  def sense(self):
    pass
    
"""
    promise_path = os.path.join(self.plugin_dir, promise_name)
    self.writeFile(promise_path, promise_content)
    self.writeInit()
    promise_process = self.createPromiseProcess(promise_name)

    with self.assertRaises(RuntimeError) as exc:
      promise_module = promise_process._loadPromiseModule()

    self.assertEquals(exc.exception.message, 'RunPromise class is not a subclass of GenericPromise class.')

  def test_promise_match_interface_no_sense(self):
    promise_name = 'my_promise_nosense.py'
    promise_content = """from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise import GenericPromise

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    pass

  def noSenseMethod(self):
    pass
    
"""
    promise_path = os.path.join(self.plugin_dir, promise_name)
    self.writeFile(promise_path, promise_content)
    self.writeInit()
    promise_process = self.createPromiseProcess(promise_name)

    with self.assertRaises(TypeError) as exc:
      promise_module = promise_process._loadPromiseModule()
      promise = promise_module.RunPromise({})
    self.assertEquals(exc.exception.message,
      "Can't instantiate abstract class RunPromise with abstract methods sense")

  def test_promise_extra_config(self):
    promise_name = 'my_promise_extra.py'
    config_dict = {'foo': 'bar', 'my-config': 4522111,
                   'text': 'developers \ninformation, sample\n\ner'}
    promise_content = """from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise import GenericPromise

%(config_name)s = %(config_content)s

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def sense(self):
    pass
    
""" % {'config_name': PROMISE_PARAMETER_NAME,
       'config_content': config_dict}
    promise_path = os.path.join(self.plugin_dir, promise_name)
    self.writeFile(promise_path, promise_content)
    self.writeInit()
    promise_process = self.createPromiseProcess(promise_name)
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(promise_process.argument_dict)

    self.assertEquals(promise.getConfig('foo'), 'bar')
    self.assertEquals(promise.getConfig('my-config'), 4522111)
    self.assertEquals(promise.getConfig('text'), config_dict['text'])

  def test_promise_extra_config_reserved_name(self):
    promise_name = 'my_promise_extra.py'
    config_dict = {'name': 'bar', 'my-config': 4522111}
    promise_content = """from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise import GenericPromise

%(config_name)s = %(config_content)s

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def sense(self):
    pass
    
""" % {'config_name': PROMISE_PARAMETER_NAME,
       'config_content': config_dict}
    promise_path = os.path.join(self.plugin_dir, promise_name)
    self.writeFile(promise_path, promise_content)
    self.writeInit()
    promise_process = self.createPromiseProcess(promise_name)

    with self.assertRaises(ValueError) as exc:
      promise_module = promise_process._loadPromiseModule()
    self.assertEquals(exc.exception.message, "Extra parameter name 'name' cannot be used.\n%s" % config_dict)

  def test_runpromise(self):
    promise_name = 'my_promise.py'
    self.configureLauncher()
    self.generatePromiseScript(promise_name, success=True)
    state_folder = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertTrue(os.path.exists(state_folder))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))

    expected_result = """{
  "result": {
    "failed": false,
    "message": "success",
    "type": "Test Result"
  },
  "path": "%s/my_promise.py",
  "name": "my_promise.py",
  "execution-time": 0.1,
  "title": "my_promise"
}""" % self.plugin_dir
    state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME, 'my_promise.status.json')
    self.assertTrue(os.path.exists(state_file))
    with open(state_file) as f:
      result_dict = json.loads(f.read())
      result_dict['result'].pop('date')
      self.assertEquals(json.loads(expected_result), result_dict)

  def test_runpromise_multiple(self):
    promise_name = 'my_promise.py'
    second_name = 'my_second_promise.py'
    self.configureLauncher()
    self.generatePromiseScript(promise_name, success=True)
    self.generatePromiseScript(second_name, success=True)
    state_folder = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertTrue(os.path.exists(state_folder))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))

    expected_result = """{
  "result": {
    "failed": false,
    "message": "success",
    "type": "Test Result"
  },
  "path": "%(promise_dir)s/%(name)s.py",
  "name": "%(name)s.py",
  "execution-time": 0.1,
  "title": "%(name)s"
}"""

    # first promise
    state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME, 'my_promise.status.json')
    self.assertTrue(os.path.exists(state_file))
    with open(state_file) as f:
      result_dict = json.loads(f.read())
      result_dict['result'].pop('date')
      expected_dict = expected_result % {'promise_dir': self.plugin_dir, 'name': 'my_promise'}
      self.assertEquals(json.loads(expected_dict), result_dict)

    # second promise
    state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME, 'my_second_promise.status.json')
    self.assertTrue(os.path.exists(state_file))
    with open(state_file) as f:
      result_dict = json.loads(f.read())
      result_dict['result'].pop('date')
      expected_dict = expected_result % {'promise_dir': self.plugin_dir, 'name': 'my_second_promise'}
      self.assertEquals(json.loads(expected_dict), result_dict)

  def test_runpromise_no_logdir(self):
    promise_name = 'my_promise.py'
    # no promise log output dir
    self.configureLauncher(logdir=False)
    self.generatePromiseScript(promise_name, success=True)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertTrue(os.path.exists(state_file))
    self.assertFalse(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))

  def test_runpromise_savemethod(self):
    promise_name = 'my_promise.py'
    def test_method(result):
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, TestResult))
      self.assertTrue(result.execution_time != 0)
      self.assertEquals(result.title, 'my_promise')
      self.assertEquals(result.name, promise_name)
      self.assertEquals(result.path, os.path.join(self.plugin_dir, promise_name))
      self.assertEquals(result.item.message, "success")
      self.assertEquals(result.item.hasFailed(), False)
      self.assertTrue(isinstance(result.item.date, datetime))

    self.configureLauncher(save_method=test_method)
    self.generatePromiseScript(promise_name, success=True)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertTrue(os.path.exists(state_file))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))

  def test_runpromise_savemethod_no_logdir(self):
    promise_name = 'my_promise.py'
    def test_method(result):
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, TestResult))
      self.assertTrue(result.execution_time != 0)
      self.assertEquals(result.title, 'my_promise')
      self.assertEquals(result.name, promise_name)
      self.assertEquals(result.path, os.path.join(self.plugin_dir, promise_name))
      self.assertEquals(result.item.message, "success")
      self.assertEquals(result.item.hasFailed(), False)
      self.assertTrue(isinstance(result.item.date, datetime))

    # no promise log output dir
    self.configureLauncher(logdir=False, save_method=test_method)
    self.generatePromiseScript(promise_name, success=True)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertTrue(os.path.exists(state_file))
    self.assertFalse(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))

  def test_runpromise_savemethod_anomaly(self):
    promise_name = 'my_promise.py'
    def test_method(result):
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, AnomalyResult))
      self.assertTrue(result.execution_time != 0)
      self.assertEquals(result.title, 'my_promise')
      self.assertEquals(result.name, promise_name)
      self.assertEquals(result.path, os.path.join(self.plugin_dir, promise_name))
      self.assertEquals(result.item.message, "success")
      self.assertEquals(result.item.hasFailed(), False)
      self.assertTrue(isinstance(result.item.date, datetime))

    self.configureLauncher(save_method=test_method, enable_anomaly=True)
    self.generatePromiseScript(promise_name, success=True)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertTrue(os.path.exists(state_file))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))

  def test_runpromise_savemethod_multiple(self):
    promise_name = 'my_promise.py'
    promise_failed = 'my_failed_promise.py'
    self.counter = 0
    def test_method(result):
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, TestResult))
      self.assertTrue(result.name in [promise_failed, promise_name])
      if result.name == promise_failed:
        self.assertEquals(result.item.hasFailed(), True)
        self.assertEquals(result.item.message, "failed")
      else:
        self.assertEquals(result.item.hasFailed(), False)
        self.assertEquals(result.item.message, "success")
      self.counter += 1

    self.configureLauncher(save_method=test_method)
    self.generatePromiseScript(promise_name, success=True)
    self.generatePromiseScript(promise_failed, success=False)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertEquals(self.counter, 2)
    self.assertTrue(os.path.exists(state_file))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_promise.log')))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_failed_promise.log')))

  def test_runpromise_savemethod_multiple_success(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    third_promise = 'my_third_promise.py'
    self.counter = 0
    def test_method(result):
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, TestResult))
      self.assertTrue(result.name in [first_promise, second_promise, third_promise])
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")
      self.counter += 1

    self.configureLauncher(save_method=test_method)
    self.generatePromiseScript(first_promise, success=True)
    self.generatePromiseScript(second_promise, success=True)
    self.generatePromiseScript(third_promise, success=True)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)

    # run promise will not fail
    self.launcher.run()
    self.assertEquals(self.counter, 3)
    self.assertTrue(os.path.exists(state_file))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_first_promise.log')))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_second_promise.log')))
    self.assertTrue(os.path.exists(os.path.join(self.log_dir, 'my_third_promise.log')))

  def test_runpromise_fail_and_success(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'

    self.configureLauncher()
    self.generatePromiseScript(first_promise, success=True)
    self.generatePromiseScript(second_promise, success=False)

    # run promise will fail when promise fail (usefull for slapgrid)
    with self.assertRaises(PromiseError) as exc:
      self.launcher.run()
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % second_promise)

    # force to reload the module without rerun python
    os.system('rm %s/*.pyc' % self.plugin_dir)
    self.generatePromiseScript(second_promise, success=True)
    # wait next periodicity
    time.sleep(2)
    self.launcher.run()

    log_file = os.path.join(self.log_dir, 'my_second_promise.log')
    self.assertTrue(os.path.exists(log_file))
    with open(log_file) as f:
      line = f.readline()
      self.assertTrue('failed' in line, line)
      line = f.readline()
      self.assertTrue('success' in line, line)


  def test_runpromise_with_periodicity(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    self.counter = 0

    def test_method_first(result):
      self.assertTrue(result.name in [first_promise, second_promise])
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")
      self.counter += 1

    def test_method_one(result):
      self.counter += 1
      self.assertEquals(result.name, first_promise)
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")

    self.configureLauncher(save_method=test_method_first)
    # ~2 seconds
    self.generatePromiseScript(first_promise, success=True, periodicity=0.03)
    # ~3 seconds
    self.generatePromiseScript(second_promise, success=True, periodicity=0.05)

    self.launcher.run()
    self.assertEquals(self.counter, 2)

    self.configureLauncher(save_method=test_method_one)
    time.sleep(2)
    self.counter = 0
    self.launcher.run() # only my_first_promise will run
    self.assertEquals(self.counter, 1)

    time.sleep(3)
    self.counter = 0
    self.configureLauncher(save_method=test_method_first)
    self.launcher.run()
    self.assertEquals(self.counter, 2)

  def test_runpromise_with_periodicity_same(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    self.counter = 0

    def test_method(result):
      self.assertTrue(result.name in [first_promise, second_promise])
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")
      self.counter += 1

    self.configureLauncher(save_method=test_method)
    # ~2 seconds
    self.generatePromiseScript(first_promise, success=True, periodicity=0.03)
    self.generatePromiseScript(second_promise, success=True, periodicity=0.03)

    self.launcher.run()
    self.assertEquals(self.counter, 2)

    self.configureLauncher(save_method=test_method)
    time.sleep(1)
    self.counter = 0
    self.launcher.run() # run nothing
    self.assertEquals(self.counter, 0)

    time.sleep(1)
    self.counter = 0
    self.configureLauncher(save_method=test_method)
    self.launcher.run()
    self.assertEquals(self.counter, 2)

  def test_runpromise_with_periodicity_result_failed(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    first_state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME,
                                    'my_first_promise.status.json')
    second_state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME,
                                     'my_second_promise.status.json')

    self.configureLauncher()
    # ~2 seconds
    self.generatePromiseScript(first_promise, success=True, periodicity=0.03)
    # ~3 seconds
    self.generatePromiseScript(second_promise, success=False, periodicity=0.05)

    with self.assertRaises(PromiseError) as exc:
      self.launcher.run()
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % second_promise)

    self.assertTrue(os.path.exists(first_state_file))
    self.assertTrue(os.path.exists(second_state_file))
    first_result = json.load(open(first_state_file))
    second_result = json.load(open(second_state_file))
    self.assertEquals(first_result['name'], first_promise)
    self.assertEquals(second_result['name'], second_promise)
    first_date = first_result['result']['date']
    second_date = second_result['result']['date']

    self.configureLauncher()
    time.sleep(2)
    with self.assertRaises(PromiseError) as exc:
      self.launcher.run() # only my_first_promise will run but second_promise still failing
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % second_promise)

    first_result = json.load(open(first_state_file))
    second_result = json.load(open(second_state_file))
    self.assertNotEquals(first_result['result']['date'], first_date)
    self.assertEquals(second_result['result']['date'], second_date)
    first_date = first_result['result']['date']

    time.sleep(3)
    self.configureLauncher()
    with self.assertRaises(PromiseError) as exc:
      self.launcher.run()
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % second_promise)

    first_result = json.load(open(first_state_file))
    second_result = json.load(open(second_state_file))
    self.assertNotEquals(first_result['result']['date'], first_date)
    self.assertNotEquals(second_result['result']['date'], second_date)

  def test_runpromise_with_periodicity_result_failed_and_ok(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    first_state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME,
                                    'my_first_promise.status.json')
    second_state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME,
                                     'my_second_promise.status.json')

    self.configureLauncher()
    # ~2 seconds
    self.generatePromiseScript(first_promise, success=True, periodicity=0.03)
    # ~3 seconds
    self.generatePromiseScript(second_promise, success=False, periodicity=0.05)

    with self.assertRaises(PromiseError) as exc:
      self.launcher.run()
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % second_promise)

    self.assertTrue(os.path.exists(first_state_file))
    self.assertTrue(os.path.exists(second_state_file))
    first_result = json.load(open(first_state_file))
    second_result = json.load(open(second_state_file))
    self.assertEquals(first_result['name'], first_promise)
    self.assertEquals(second_result['name'], second_promise)
    first_date = first_result['result']['date']
    second_date = second_result['result']['date']

    self.configureLauncher()
    time.sleep(2)
    with self.assertRaises(PromiseError) as exc:
      self.launcher.run() # only my_first_promise will run but second_promise still failing
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % second_promise)

    first_result = json.load(open(first_state_file))
    second_result = json.load(open(second_state_file))
    self.assertNotEquals(first_result['result']['date'], first_date)
    self.assertEquals(second_result['result']['date'], second_date)
    first_date = first_result['result']['date']
    second_date = second_result['result']['date']

    time.sleep(4)
    # force to reload the module without rerun python
    os.system('rm %s/*.pyc' % self.plugin_dir)

    # second_promise is now success
    self.generatePromiseScript(second_promise, success=True, periodicity=0.05)
    self.configureLauncher()
    self.launcher.run() # now all succeed

    first_result = json.load(open(first_state_file))
    second_result = json.load(open(second_state_file))
    self.assertNotEquals(first_result['result']['date'], first_date)
    self.assertNotEquals(second_result['result']['date'], second_date)

  def test_runpromise_force(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    self.counter = 0

    def test_method(result):
      self.assertTrue(result.name in [first_promise, second_promise])
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")
      self.counter += 1

    self.configureLauncher(save_method=test_method)
    # ~2 seconds
    self.generatePromiseScript(first_promise, success=True, periodicity=0.03)
    self.generatePromiseScript(second_promise, success=True, periodicity=0.03)

    self.launcher.run()
    self.assertEquals(self.counter, 2)

    self.configureLauncher(save_method=test_method)
    time.sleep(1)
    self.counter = 0
    self.launcher.run() # run nothing
    self.assertEquals(self.counter, 0)

    self.configureLauncher(save_method=test_method, force=True)
    self.counter = 0
    self.launcher.run() # will run all as force is True
    self.assertEquals(self.counter, 2)

    self.configureLauncher(save_method=test_method)
    time.sleep(1)
    self.counter = 0
    self.launcher.run() # run nothing
    self.assertEquals(self.counter, 0)

    time.sleep(1)
    self.counter = 0
    self.configureLauncher(save_method=test_method)
    self.launcher.run() # after 2 seconds will run all
    self.assertEquals(self.counter, 2)

  def test_runpromise_wrapped(self):
    promise_name = "my_bash_promise"
    promise_path = os.path.join(self.legacy_promise_dir, promise_name)
    self.called = False
    with open(promise_path, 'w') as f:
      f.write("""#!/bin/bash
echo "success"
""")
    os.chmod(promise_path, 0744)

    def test_method(result):
      self.called = True
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, TestResult))
      self.assertTrue(result.execution_time != 0)
      self.assertEquals(result.title, promise_name)
      self.assertEquals(result.name, promise_name)
      self.assertEquals(result.path, os.path.join(self.legacy_promise_dir, promise_name))
      self.assertEquals(result.item.message, "success")
      self.assertEquals(result.item.hasFailed(), False)
      self.assertTrue(isinstance(result.item.date, datetime))

    self.configureLauncher(save_method=test_method)
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)
    self.launcher.run()

    self.assertTrue(self.called)
    self.assertTrue(os.path.exists(state_file))

  def test_runpromise_wrapped_failed(self):
    promise_name = "my_bash_promise"
    promise_path = os.path.join(self.legacy_promise_dir, promise_name)
    with open(promise_path, 'w') as f:
      f.write("""#!/bin/bash
echo "This promise failed"
exit 1
""")
    os.chmod(promise_path, 0744)

    self.configureLauncher()
    state_file = os.path.join(self.partition_dir, PROMISE_STATE_FOLDER_NAME)
    with self.assertRaises(PromiseError) as exc:
      self.launcher.run()
    self.assertEquals(exc.exception.message, 'Promise %r failed.' % promise_name)

  def test_runpromise_wrapped_mixed(self):
    self.called = 0
    result_dict = {"my_bash_promise": "", "my_bash_promise2": "", "first_promise.py": "", "second_promise.py": ""}
    def test_method(result):
      self.called += 1
      result_dict.pop(result.name)
      if result.title == "first_promise" or result.title == "second_promise":
        self.assertEquals(result.item.message, "success")
      if result.title == "my_bash_promise":
        self.assertEquals(result.item.message, "promise 1 succeeded")
      if result.title == "my_bash_promise2":
        self.assertEquals(result.item.message, "promise 2 succeeded")
      self.assertEquals(result.item.hasFailed(), False)

    promise_name = "my_bash_promise"
    promise_path = os.path.join(self.legacy_promise_dir, promise_name)
    promise_name2 = "my_bash_promise2"
    promise_path2 = os.path.join(self.legacy_promise_dir, promise_name2)
    with open(promise_path, 'w') as f:
      f.write("""#!/bin/bash
echo "promise 1 succeeded"
exit 0
""")
    os.chmod(promise_path, 0744)
    with open(promise_path2, 'w') as f:
      f.write("""#!/bin/bash
echo "promise 2 succeeded"
exit 0
""")
    os.chmod(promise_path2, 0744)
    self.generatePromiseScript("first_promise.py", success=True)
    self.generatePromiseScript("second_promise.py", success=True)

    self.configureLauncher(save_method=test_method)
    self.launcher.run()
    self.assertEquals(self.called, 4)


  def test_runpromise_run_only(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    third_promise = 'my_third_promise.py'
    self.counter = 0
    self.check_list = [first_promise, second_promise, third_promise]
    def test_method(result):
      self.assertTrue(result.name in self.check_list)
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")
      self.counter += 1

    self.configureLauncher(save_method=test_method)
    self.generatePromiseScript(first_promise, success=True)
    self.generatePromiseScript(second_promise, success=True)
    self.generatePromiseScript(third_promise, success=True)

    # run promise will not fail
    self.launcher.run()
    self.assertEquals(self.counter, 3)

    self.counter = 0
    self.check_list = [second_promise]
    self.configureLauncher(save_method=test_method, run_list=[second_promise], force=True)
    time.sleep(1)
    self.launcher.run()
    self.assertEquals(self.counter, 1)

  def test_runpromise_run_only_multiple(self):
    first_promise = 'my_first_promise.py'
    second_promise = 'my_second_promise.py'
    third_promise = 'my_third_promise.py'
    self.counter = 0
    self.check_list = [first_promise, second_promise, third_promise]
    def test_method(result):
      self.assertTrue(result.name in self.check_list)
      self.assertEquals(result.item.hasFailed(), False)
      self.assertEquals(result.item.message, "success")
      self.counter += 1

    self.configureLauncher(save_method=test_method)
    self.generatePromiseScript(first_promise, success=True)
    self.generatePromiseScript(second_promise, success=True)
    self.generatePromiseScript(third_promise, success=True)

    # run promise will not fail
    self.launcher.run()
    self.assertEquals(self.counter, 3)

    self.counter = 0
    self.check_list = [third_promise, second_promise]
    self.configureLauncher(save_method=test_method, run_list=self.check_list, force=True)
    time.sleep(1)
    self.launcher.run()
    self.assertEquals(self.counter, 2)

  def writeLatestPromiseResult(self):
    state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME, 'my_promise.status.json')
    result_string = """{
  "result": {
    "failed": true,
    "message": "error",
    "date": "%s",
    "type": "Test Result"
  },
  "path": "%s/my_promise.py",
  "name": "my_promise.py",
  "execution-time": 0.1,
  "title": "my_promise"
}""" % (datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'), self.plugin_dir)

    if not os.path.exists(os.path.dirname(state_file)):
      os.makedirs(os.path.dirname(state_file))
    with open(state_file, 'w') as f:
      f.write(result_string)

  def writeLatestBashPromiseResult(self, name="my_bash_promise"):
    state_file = os.path.join(self.partition_dir, PROMISE_RESULT_FOLDER_NAME,
                              '%s.status.json' % name)
    result_string = """{
  "result": {
    "failed": true,
    "message": "error",
    "date": "%(date)s",
    "type": "Test Result"
  },
  "path": "%(folder)s/%(name)s",
  "name": "%(name)s",
  "execution-time": 0.1,
  "title": "%(name)s"
}""" % {'date': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
        'folder': self.legacy_promise_dir,
        'name': name}

    if not os.path.exists(os.path.dirname(state_file)):
      os.makedirs(os.path.dirname(state_file))
    with open(state_file, 'w') as f:
      f.write(result_string)

  def test_runpromise_will_timeout(self):
    self.called = False
    promise_name = 'my_promise.py'
    self.writeLatestPromiseResult()

    def test_method(result):
      self.called = True
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, AnomalyResult))
      self.assertTrue(result.execution_time >= 1)
      self.assertEquals(result.title, 'my_promise')
      self.assertEquals(result.name, promise_name)
      self.assertTrue("Promise timed out after" in result.item.message)
      self.assertEquals(result.item.hasFailed(), True)

    self.configureLauncher(save_method=test_method, enable_anomaly=True, timeout=1)
    self.generatePromiseScript(promise_name, success=True, content="""import time
    time.sleep(20)""")

    # run promise will timeout
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertTrue(self.called)

  def test_runpromise_wrapped_will_timeout(self):
    promise_name = "my_bash_promise"
    promise_path = os.path.join(self.legacy_promise_dir, promise_name)
    self.writeLatestBashPromiseResult()
    self.called = False
    with open(promise_path, 'w') as f:
      f.write("""#!/bin/bash
sleep 20
echo "success"
""")
    os.chmod(promise_path, 0744)

    def test_method(result):
      self.called = True
      self.assertTrue(isinstance(result, PromiseQueueResult))
      self.assertTrue(isinstance(result.item, TestResult))
      self.assertTrue(result.execution_time >= 1)
      self.assertEquals(result.title, promise_name)
      self.assertEquals(result.name, promise_name)
      self.assertEquals(result.path, promise_path)
      self.assertTrue("Promise timed out after" in result.item.message)
      self.assertEquals(result.item.hasFailed(), True)
      self.assertTrue(isinstance(result.item.date, datetime))

    self.configureLauncher(save_method=test_method, timeout=1)
    # run promise will timeout
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertTrue(self.called)

  def test_runpromise_wrapped_will_timeout_two(self):
    first_promise = "my_bash_promise"
    first_promise_path = os.path.join(self.legacy_promise_dir, first_promise)
    second_promise = "my_second_bash_promise"
    second_promise_path = os.path.join(self.legacy_promise_dir, second_promise)
    self.writeLatestBashPromiseResult(first_promise)
    self.writeLatestBashPromiseResult(second_promise)

    def createPromise(promise_path):
      with open(promise_path, 'w') as f:
        f.write("""#!/bin/bash
echo "some data from promise"
sleep 20
echo "success"
exit 1
""")
      os.chmod(promise_path, 0744)

    createPromise(first_promise_path)
    createPromise(second_promise_path)
    self.configureLauncher(timeout=0.5)
    # run promise will timeout
    with self.assertRaises(PromiseError):
      self.launcher.run()

  def test_runpromise_timeout_fail_if_test(self):
    promise_name = 'my_promise.py'

    self.configureLauncher(timeout=1, enable_anomaly=False)
    self.generatePromiseScript(promise_name, success=True, content="""import time
    time.sleep(20)""", periodicity=0.01)

    # timeout for the first time and raise
    with self.assertRaises(PromiseError):
      self.launcher.run()

  def test_runpromise_fail_if_timeout_twice(self):
    promise_name = 'my_promise.py'

    self.configureLauncher(timeout=1, enable_anomaly=True)
    self.generatePromiseScript(promise_name, success=True, content="""import time
    time.sleep(20)""", periodicity=0.01)

    # timeout for the first time, no raise
    self.launcher.run()

    # run promise will timeout and raise
    time.sleep(1)
    with self.assertRaises(PromiseError):
      self.launcher.run()

    # run promise will continue to raise
    time.sleep(1)
    with self.assertRaises(PromiseError):
      self.launcher.run()

class TestSlapOSGenericPromise(TestSlapOSPromiseMixin):

  def initialisePromise(self, promise_content="", success=True, timeout=60):
    self.promise_name = 'my_promise.py'
    self.promise_path = os.path.join(self.plugin_dir, self.promise_name)
    self.configureLauncher()
    self.generatePromiseScript(self.promise_name, periodicity=1, content=promise_content, success=success)
    self.writeInit()
    self.queue = Queue.Queue()
    self.promise_config = {
      'log-folder': self.log_dir,
      'partition-folder': self.partition_dir,
      'promise-timeout': timeout,
      'debug': False,
      'check-anomaly': True,
      'master-url': "https://master.url.com",
      'partition-cert': '',
      'partition-key': '',
      'partition-id': self.partition_id,
      'computer-id': self.computer_id,
      'queue': self.queue,
      'path': self.promise_path,
      'name': self.promise_name
    }

  def createPromiseProcess(self, check_anomaly=False, wrap=False):

    logging.basicConfig()
    return PromiseProcess(
      self.partition_dir,
      self.promise_name,
      self.promise_path,
      logger=logging.getLogger('grid.promise'),
      argument_dict=self.promise_config,
      check_anomaly=check_anomaly,
      wrap=wrap,
    )

  def test_create_simple_promise(self):
    self.initialisePromise()
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)
    self.assertEquals(promise.getPeriodicity(), 1)
    self.assertEquals(promise.getName(), self.promise_name)
    self.assertEquals(promise.getTitle(), 'my_promise')
    self.assertEquals(promise.getPartitionFolder(), self.partition_dir)
    self.assertEquals(promise.getPromiseFile(), self.promise_path)
    self.assertEquals(promise.getLogFolder(), self.log_dir)
    self.assertEquals(promise.getLogFile(), os.path.join(self.log_dir, 'my_promise.log'))

    promise.setPeriodicity(2)
    self.assertEquals(promise.getPeriodicity(), 2)
    with self.assertRaises(ValueError):
      promise.setPeriodicity(0)

    promise.run(check_anomaly=True)
    result = self.queue.get(True, 1)
    self.assertTrue(isinstance(result, PromiseQueueResult))
    self.assertTrue(isinstance(result.item, AnomalyResult))
    self.assertEquals(result.title, 'my_promise')
    self.assertEquals(result.name, self.promise_name)
    self.assertEquals(result.path, os.path.join(self.plugin_dir, self.promise_name))
    self.assertEquals(result.item.message, "success")
    self.assertEquals(result.item.hasFailed(), False)
    self.assertTrue(isinstance(result.item.date, datetime))

  def test_promise_anomaly_disabled(self):
    self.initialisePromise()
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    promise.run()
    result = self.queue.get(True, 1)
    self.assertTrue(isinstance(result, PromiseQueueResult))
    self.assertTrue(isinstance(result.item, TestResult))
    self.assertEquals(result.title, 'my_promise')
    self.assertEquals(result.name, self.promise_name)
    self.assertEquals(result.path, os.path.join(self.plugin_dir, self.promise_name))
    self.assertEquals(result.item.message, "success")
    self.assertEquals(result.item.hasFailed(), False)
    self.assertTrue(isinstance(result.item.date, datetime))

  def test_promise_with_raise(self):
    promise_content = "raise ValueError('Bad Promise raised')"
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    # no raise
    promise.run()
    result = self.queue.get(True, 1)
    self.assertEquals(result.title, 'my_promise')
    self.assertEquals(result.name, self.promise_name)
    self.assertEquals(result.item.message, "Bad Promise raised")
    self.assertEquals(result.item.hasFailed(), True)

  def test_promise_no_return(self):
    promise_content = "return"
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    # no raise
    promise.run()
    result = self.queue.get(True, 1)
    self.assertEquals(result.title, 'my_promise')
    self.assertEquals(result.name, self.promise_name)
    self.assertEquals(result.item.message, "No result found!")
    self.assertEquals(result.item.hasFailed(), False)

  def test_promise_resultfromlog(self):
    promise_content = "self.logger.info('Promise is running...')"
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    date = datetime.now()
    promise.sense()
    # get all messages during the latest minute
    latest_message_list = promise.getLastPromiseResultList(result_count=1)
    date = datetime.strptime(date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    self.assertEquals(len(latest_message_list), 1)
    self.assertEquals(
      latest_message_list[0][0],
      {'date': date, 'status': 'INFO', 'message': 'Promise is running...'})
    self.assertEquals(
      latest_message_list[0][1],
      {'date': date, 'status': 'INFO', 'message': 'success'})

  def test_promise_resultfromlog_error(self):
    promise_content = 'self.logger.error("Promise is running...\\nmessage in new line")'
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    date = datetime.now()
    promise.sense()
    # get all messages during the latest minute
    latest_message_list = promise.getLastPromiseResultList(result_count=1)
    date = datetime.strptime(date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    self.assertEquals(len(latest_message_list), 1)
    self.assertEquals(
      latest_message_list[0][0],
      {'date': date, 'status': 'ERROR',
       'message': 'Promise is running...\nmessage in new line'})
    self.assertEquals(
      latest_message_list[0][1],
      {'date': date, 'status': 'INFO', 'message': 'success'})

  def test_promise_resultfromlog_no_logfolder(self):
    self.log_dir = None
    promise_content = "self.logger.info('Promise is running...')"
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    date = datetime.now()
    promise.sense()
    self.assertEquals(promise.getLogFolder(), None)
    self.assertEquals(promise.getLogFile(), None)

    # get all messages during the latest minute
    latest_message_list = promise.getLastPromiseResultList(result_count=1)
    date = datetime.strptime(date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    self.assertEquals(len(latest_message_list), 1)
    self.assertEquals(
      latest_message_list[0][0],
      {'date': date, 'status': 'INFO', 'message': 'Promise is running...'})
    self.assertEquals(
      latest_message_list[0][1],
      {'date': date, 'status': 'INFO', 'message': 'success'})

  def test_promise_resultfromlog_latest_minutes(self):
    self.initialisePromise(timeout=60)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    # write some random logs
    start_date = datetime.now()
    with open(promise.getLogFile(), 'w') as f:
      for i in range(0, 50):
        transaction_id = '%s-%s' % (int(time.time()), random.randint(100, 999))
        date = start_date - timedelta(minutes=(49 - i))
        date_string = date.strftime('%Y-%m-%d %H:%M:%S')
        line = "%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, i)
        f.write(line)

    latest_message_list = promise.getLastPromiseResultList(
      latest_minute=10,
      result_count=100
    )
    start_date = datetime.strptime(start_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    end_date_string = (start_date - timedelta(minutes=9)).strftime('%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d %H:%M:%S')
    self.assertEquals(len(latest_message_list), 10)
    for message in latest_message_list:
      self.assertEquals(len(message), 1)
    self.assertEquals(
      latest_message_list[0][0],
      {'date': start_date, 'status': 'INFO', 'message': 'Promise result 49'})
    self.assertEquals(
      latest_message_list[-1][0],
      {'date': end_date, 'status': 'INFO', 'message': 'Promise result 40'})

  def test_promise_resultfromlog_latest_minutes_multilog(self):
    self.initialisePromise(timeout=60)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    # write some random logs
    start_date = datetime.now()
    date = start_date
    line_list = []
    j = 0
    for i in range(0, 25):
      transaction_id = '%s-%s' % (int(time.time()), random.randint(100, 999))
      date_string = date.strftime('%Y-%m-%d %H:%M:%S')
      line_list.append("%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, j))
      date = date - timedelta(seconds=30)
      j += 1
      date_string = date.strftime('%Y-%m-%d %H:%M:%S')
      line_list.append("%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, j))
      date = date - timedelta(seconds=30)
      j += 1

    line_list.reverse()
    with open(promise.getLogFile(), 'w') as f:
      f.write('\n'.join(line_list))

    latest_message_list = promise.getLastPromiseResultList(
      latest_minute=10,
      result_count=100
    )

    start_date = datetime.strptime(start_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    end_date_string = (start_date - timedelta(seconds=30*19)).strftime('%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d %H:%M:%S')
    # there is 2 result line per minutes
    self.assertEquals(len(latest_message_list), 10)
    for message in latest_message_list:
      self.assertEquals(len(message), 2)
    self.assertEquals(
      latest_message_list[0][1],
      {'date': start_date, 'status': 'INFO', 'message': 'Promise result 0'})
    self.assertEquals(
      latest_message_list[-1][0],
      {'date': end_date, 'status': 'INFO', 'message': 'Promise result 19'})

  def test_promise_resultfromlog_result_count(self):
    self.initialisePromise()
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    # write some random logs
    start_date = datetime.now()
    date = start_date
    line_list = []
    j = 0
    for i in range(0, 25):
      transaction_id = '%s-%s' % (int(time.time()), random.randint(100, 999))
      date_string = date.strftime('%Y-%m-%d %H:%M:%S')
      line_list.append("%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, j))
      date = date - timedelta(seconds=30)
      j += 1
      date_string = date.strftime('%Y-%m-%d %H:%M:%S')
      line_list.append("%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, j))
      date = date - timedelta(seconds=30)
      j += 1

    line_list.reverse()
    with open(promise.getLogFile(), 'w') as f:
      f.write('\n'.join(line_list))

    # result_count = 2 will return 2 log
    # max execution time is 1 min and log is writen every 30 seconds
    latest_message_list = promise.getLastPromiseResultList(result_count=1)

    start_date = datetime.strptime(start_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    end_date_string = (start_date - timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d %H:%M:%S')
    # there is 2 result line per minutes
    self.assertEquals(len(latest_message_list), 1)
    self.assertEquals(
      latest_message_list[0][0],
      {'date': end_date, 'status': 'INFO', 'message': 'Promise result 1'})
    self.assertEquals(
      latest_message_list[0][1],
      {'date': start_date, 'status': 'INFO', 'message': 'Promise result 0'})

  def test_promise_resultfromlog_result_count_many(self):
    self.initialisePromise()
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    # write some random logs
    start_date = datetime.now()
    date = start_date
    line_list = []
    j = 0
    for i in range(0, 25):
      transaction_id = '%s-%s' % (int(time.time()), random.randint(100, 999))
      date_string = date.strftime('%Y-%m-%d %H:%M:%S')
      line_list.append("%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, j))
      date = date - timedelta(seconds=30)
      j += 1
      date_string = date.strftime('%Y-%m-%d %H:%M:%S')
      line_list.append("%s - INFO - %s - Promise result %s\n" % (date_string, transaction_id, j))
      date = date - timedelta(seconds=30)
      j += 1

    line_list.reverse()
    with open(promise.getLogFile(), 'w') as f:
      f.write('\n'.join(line_list))

    # result_count = 2 will return 4 log
    # max execution time is 1 min and log is writen every 30 seconds
    latest_message_list = promise.getLastPromiseResultList(result_count=2)

    start_date = datetime.strptime(start_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    end_date_string = (start_date - timedelta(seconds=30*3)).strftime('%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d %H:%M:%S')
    # there is 2 result line per minutes
    self.assertEquals(len(latest_message_list), 2)
    for message in latest_message_list:
      self.assertEquals(len(message), 2)
    self.assertEquals(
      latest_message_list[0][1],
      {'date': start_date, 'status': 'INFO', 'message': 'Promise result 0'})
    self.assertEquals(
      latest_message_list[-1][0],
      {'date': end_date, 'status': 'INFO', 'message': 'Promise result 3'})

    latest_message_list = promise.getLastPromiseResultList(result_count=100)
    # all results
    self.assertEquals(len(latest_message_list), 25)

  def test_promise_defaulttest(self):
    promise_content = 'self.logger.info("Promise is running...\\nmessage in new line")'
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    promise.sense()

    result = promise._test(result_count=1, failure_amount=1)
    self.assertTrue(isinstance(result, TestResult))
    self.assertEquals(result.message, 'Promise is running...\nmessage in new line\nsuccess')
    self.assertEquals(result.hasFailed(), False)

  def test_promise_defaulttest_failure(self):
    self.initialisePromise(success=False)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    promise.sense()

    result = promise._test(result_count=1, failure_amount=1)
    self.assertTrue(isinstance(result, TestResult))
    self.assertEquals(result.message, 'failed')
    self.assertEquals(result.hasFailed(), True)

  def test_promise_defaulttest_error_if_two_fail(self):
    self.initialisePromise(success=False, timeout=1)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    promise.sense()

    # fail if 2 errors found
    result = promise._test(result_count=2, failure_amount=2)
    self.assertTrue(isinstance(result, TestResult))
    self.assertEquals(result.message, 'failed')
    self.assertEquals(result.hasFailed(), False)

    self.initialisePromise(success=False, timeout=1)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)
    promise.sense()
    result = promise._test(result_count=2, failure_amount=2)
    self.assertEquals(result.message, 'failed')
    self.assertEquals(result.hasFailed(), True)

    # will continue to fail
    self.initialisePromise(success=False, timeout=1)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)
    promise.sense()
    result = promise._test(result_count=2, failure_amount=2)
    self.assertEquals(result.message, 'failed')
    self.assertEquals(result.hasFailed(), True)

  def test_promise_defaulttest_anomaly(self):
    promise_content = 'self.logger.info("Promise is running...\\nmessage in new line")'
    self.initialisePromise(promise_content)
    promise_process = self.createPromiseProcess()
    promise_module = promise_process._loadPromiseModule()
    promise = promise_module.RunPromise(self.promise_config)

    promise.sense()

    result = promise._anomaly(result_count=1, failure_amount=1)
    self.assertTrue(isinstance(result, AnomalyResult))
    self.assertEquals(result.message, 'Promise is running...\nmessage in new line\nsuccess')
    self.assertEquals(result.hasFailed(), False)


if __name__ == '__main__':
  unittest.main()

