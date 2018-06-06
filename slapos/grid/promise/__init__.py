# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2018 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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

import os
import sys
import logging
import time
import re
import json
import importlib
import traceback
import psutil
from multiprocessing import Process, Queue as MQueue
import Queue
from slapos.util import mkdir_p, chownDirectory
from slapos.grid.utils import dropPrivileges, killProcessTree
from slapos.grid.promise import interface
from slapos.grid.promise.generic import (GenericPromise, PromiseQueueResult,
                                         AnomalyResult, TestResult,
                                         PROMISE_STATE_FOLDER_NAME,
                                         PROMISE_RESULT_FOLDER_NAME,
                                         PROMISE_PARAMETER_NAME,
                                         PROMISE_PERIOD_FILE_NAME)
from slapos.grid.promise.wrapper import WrapPromise

class PromiseError(Exception):
  pass

class PromiseProcess(Process):

  """
    Run a promise in a new Process
  """

  def __init__(self, partition_folder, promise_name, promise_path, argument_dict,
      logger, allow_bang=True, uid=None, gid=None, wrap=False, 
      check_anomaly=False):
    """
      Initialise Promise Runner

      @param promise_name: The name of the promise to run
      @param promise_path: path of the promise
      @param argument_dict: all promise parameters in a dictionary
      @param allow_bang: Bolean saying if bang should be called in case of
        anomaly failure.
      @param check_anomaly: Bolean saying if promise anomaly should be run.
      @param wrap: say if the promise should be wrapped in a subprocess using
        WrapPromise class
    """
    Process.__init__(self)
    # set deamon to True, so promise process will be terminated if parent exit
    self.daemon = True
    self.name = promise_name
    self.promise_path = promise_path
    self.logger = logger
    self.allow_bang = allow_bang
    self.check_anomaly = check_anomaly
    self.argument_dict = argument_dict
    self.uid = uid
    self.gid = gid
    self.partition_folder = partition_folder
    self.wrap_promise = wrap
    self._periodicity = None
    self._timestamp_file = os.path.join(partition_folder,
                                        PROMISE_STATE_FOLDER_NAME,
                                        '%s.timestamp' % promise_name)
    periodicity_file = os.path.join(partition_folder,
                                    PROMISE_STATE_FOLDER_NAME,
                                    PROMISE_PERIOD_FILE_NAME % promise_name)
    if os.path.exists(periodicity_file) and os.stat(periodicity_file).st_size:
      with open(periodicity_file) as f:
        try:
          self._periodicity = float(f.read())
        except ValueError:
          # set to None, run the promise and regenerate the file
          pass

  def isPeriodicityMatch(self):
    """
      Return True if promise should be run now, considering the promise
        periodicity in minutes
    """
    if self._periodicity is not None and \
        os.path.exists(self._timestamp_file) and \
        os.stat(self._timestamp_file).st_size:
      with open(self._timestamp_file) as f:
        try:
          latest_timestamp = float(f.read())
          current_timediff = (time.time() - latest_timestamp) / 60.0
          if current_timediff >= self._periodicity:
            return True
          #self.logger.debug("Skip Promise %r. periodicity=%s, time_diff=%s" % (
          #    self.name, self._periodicity, current_timediff))
        except ValueError:
          # if the file is broken, run the promise and regenerate it
          return True
        else:
          return False
    return True

  def setPromiseStartTimestamp(self):
    """
      Save the promise execution timestamp
    """
    state_directory = os.path.dirname(self._timestamp_file)
    mkdir_p(state_directory)
    with open(self._timestamp_file, 'w') as f:
      f.write(str(time.time()))

  def getPromiseTitle(self):
    return os.path.splitext(self.name)[0]

  def run(self):
    """
      Run the promise
      
      This will first load the promise module (which will update process sys.path)
    """
    try:
      os.chdir(self.partition_folder)
      self.setPromiseStartTimestamp()
      if self.uid and self.gid:
        dropPrivileges(self.uid, self.gid, logger=self.logger)

      if self.wrap_promise:
        promise_instance = WrapPromise(self.argument_dict)
      else:
        self._createInitFile()
        promise_module = self._loadPromiseModule()
        promise_instance = promise_module.RunPromise(self.argument_dict)

      promise_instance.run(self.check_anomaly, self.allow_bang)
    except Exception:
      self.logger.error(traceback.format_exc())
      raise

  def _createInitFile(self):
    promise_folder = os.path.dirname(self.promise_path)
    # if there is no __init__ file, add it
    init_file = os.path.join(promise_folder, '__init__.py')
    if not os.path.exists(init_file):
      with open(init_file, 'w') as f:
        f.write("")
      os.chmod(init_file, 0644)
    # add promise folder to sys.path so we can import promise script
    if sys.path[0] != promise_folder:
      sys.path[0:0] = [promise_folder]

  def _loadPromiseModule(self):
    """Load a promise from promises directory."""

    if re.match(r'[a-zA-Z_]', self.name) is None:
      raise ValueError("Promise plugin name %r is not valid" % self.name)

    promise_module = importlib.import_module(os.path.splitext(self.name)[0])
    if not hasattr(promise_module, "RunPromise"):
      raise AttributeError("Class RunPromise not found in promise" \
        "%s" % self.name)
    if not interface.IPromise.implementedBy(promise_module.RunPromise):
      raise RuntimeError("RunPromise class in %s must implements 'IPromise'" \
        " interface. zope_interface.implements(interface.IPromise) is" \
        " missing ?" % self.name)

    from slapos.grid.promise.generic import GenericPromise
    if not issubclass(promise_module.RunPromise, GenericPromise):
      raise RuntimeError("RunPromise class is not a subclass of " \
        "GenericPromise class.")

    if promise_module.__file__ != self.promise_path:
      # cached module need to be updated
      promise_module = reload(promise_module)
    # load extra parameters
    self._loadPromiseParameterDict(promise_module)

    return promise_module

  def _loadPromiseParameterDict(self, promise_module):
    """Load a promise parameters."""
    if hasattr(promise_module, PROMISE_PARAMETER_NAME):
      extra_dict = getattr(promise_module, PROMISE_PARAMETER_NAME)
      if not isinstance(extra_dict, dict):
        raise ValueError("Extra parameter is not a dict")
      for key in extra_dict:
        if self.argument_dict.has_key(key):
          raise ValueError("Extra parameter name %r cannot be used.\n%s" % (
                           key, extra_dict))
        self.argument_dict[key] = extra_dict[key]

class PromiseLauncher(object):

  def __init__(self, config=None, logger=None, dry_run=False):
    """
      Promise launcher will run promises

      @param config_file: A file containing configurations
      @param dry_run: Only run all promises without save the result
      @param logger: Set the logger to use, if None a logger will be configured
        to console.
      @param config: A configuration dict to use. Values send here will
        overwrite configs from `config_file`. Expected values in config are:
        promise-timeout
          Maximum promise execution time before timeout. Default: 20
        partition-folder
          Base path of the partition
        promise-folder
          Promises folder, all promises scripts will be imported from that folder
        legacy-promise-folder
          Legacy promises folder, where to find bash, shell and standard promises
        log-folder
          Folder where promises will write logs. Can be None
        check-anomaly
          Ask to check anomaly instead of test. Default: False
        debug
          Configure loggin in debug mode. Default: True
        master-url
          SlapOS Master service URL
        partition-cert
          Computer Partition Certificate file
        partition-key
          Computer Partition key file
        partition-id
          Computer Partition ID, ex: slappart13
        computer-id
          Computer ID, ex: COMP-1234
        uid
          User UID
        gid
          User GID
        debug
          If True, show Promise consumption and execution time information, etc
        run-only-promise-list
          A list of promise from plugins directory that will be executed
        force
          Set to True if force run promises without check their periodicity
    """

    self.dry_run = dry_run
    self.__config = {
      'promise-timeout': 20,
      'promise-folder': None,
      'legacy-promise-folder': None,
      'log-folder': None,
      'partition-folder': None,
      'debug': False,
      'uid': None,
      'gid': None,
      'master-url': None,
      'partition-cert': None,
      'partition-key': None,
      'partition-id': None,
      'computer-id': None,
      'check-anomaly': False,
      'force': False,
      'run-only-promise-list': None
    }
    if config is not None:
      self.__config.update(config)

    for key, value in self.__config.items():
      setattr(self, key.replace('-', '_'), value or None)

    if self.promise_folder is None:
      raise ValueError("Promise folder is missing in configuration!")
    if self.partition_folder is None:
      raise ValueError("Partition folder is missing in configuration!")

    if logger is None:
      self.logger = logging.getLogger(__name__)
      self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
      if len(self.logger.handlers) == 0 or \
          not isinstance(self.logger.handlers[0], logging.StreamHandler):
        handler = logging.StreamHandler()
        handler.setFormatter(
          logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)
    else:
      self.logger = logger

    self.queue_result = MQueue()
    self.bang_called = False

    self.promise_output_dir = os.path.join(
      self.partition_folder,
      PROMISE_RESULT_FOLDER_NAME
    )
    if not os.path.exists(self.promise_output_dir):
      mkdir_p(self.promise_output_dir)
      self._updateFolderOwner()

  def _generatePromiseResult(self, promise_process, promise_name, promise_path,
      message, execution_time=0):
    if self.check_anomaly:
      problem = False
      promise_result = self._loadPromiseResult(promise_process.getPromiseTitle())
      if promise_result is not None and (promise_result.item.hasFailed() or
          'error:' in promise_result.item.message.lower()):
        # generate failure if latest promise result was error
        # If a promise timeout it will return failure if the timeout occur again
        problem = True
      result = AnomalyResult(problem=problem, message=message)
    else:
      result = TestResult(problem=True, message=message)
    return PromiseQueueResult(
      item=result,
      path=promise_path,
      name=promise_name,
      title=promise_process.getPromiseTitle(),
      execution_time=execution_time
    )

  def _savePromiseResult(self, result):
    if not isinstance(result, PromiseQueueResult):
      self.logger.error('Bad result: %s is not type of PromiseQueueResult...' % result)
      return

    promise_output_file = os.path.join(
      self.promise_output_dir,
      "%s.status.json" % result.title
    )
    promise_tmp_file = '%s.tmp' % promise_output_file

    with open(promise_tmp_file, "w") as outputfile:
      json.dump(result.serialize(), outputfile)
    os.rename(promise_tmp_file, promise_output_file)

  def _loadPromiseResult(self, promise_title):
    promise_output_file = os.path.join(
      self.promise_output_dir,
      "%s.status.json" % promise_title
    )
    result = None
    if os.path.exists(promise_output_file):
      with open(promise_output_file) as f:
        try:
          result = PromiseQueueResult()
          result.load(json.loads(f.read()))
        except ValueError, e:
          result = None
          self.logger.warn('Bad promise JSON result at %r: %s' % (
            promise_output_file,
            e
          ))
    return result

  def _emptyQueue(self):
    """Remove all entries from queue until it's empty"""
    while True:
      try:
        self.queue_result.get_nowait()
      except Queue.Empty:
        return

  def _updateFolderOwner(self, folder_path=None):
    stat_info = os.stat(self.partition_folder)
    if folder_path is None:
      folder_path = os.path.join(self.partition_folder,
                                 PROMISE_STATE_FOLDER_NAME)
    chownDirectory(folder_path, stat_info.st_uid, stat_info.st_gid)

  def _launchPromise(self, promise_name, promise_path, argument_dict,
      wrap_process=False):
    """
      Launch the promise and save the result. If promise_module is None,
      the promise will be run with the promise process wap module.

      If the promise periodicity doesn't match, the previous promise result is
      checked.
    """
    self.logger.info("Checking promise %s..." % promise_name)
    try:
      promise_process = PromiseProcess(
        self.partition_folder,
        promise_name,
        promise_path,
        argument_dict,
        logger=self.logger,
        check_anomaly=self.check_anomaly,
        allow_bang=not (self.bang_called or self.dry_run) and self.check_anomaly,
        uid=self.uid,
        gid=self.gid,
        wrap=wrap_process,
      )

      if not self.force and not promise_process.isPeriodicityMatch():
        # we won't start the promise process, just get the latest result
        result = self._loadPromiseResult(promise_process.getPromiseTitle())
        if result is not None:
          if result.item.hasFailed():
            self.logger.error(result.item.message)
            return True
        return False
      # we can do this because we run processes one by one
      # we cleanup queue in case previous result was written by a killed process
      self._emptyQueue()
      promise_process.start()
    except Exception:
      # only print traceback to not prevent run other promises
      self.logger.error(traceback.format_exc())
      self.logger.warning("Promise %s skipped." % promise_name)
      return True

    queue_item = None
    sleep_time = 0.1
    increment_limit = int(self.promise_timeout / sleep_time)
    execution_time = self.promise_timeout
    ps_profile = False
    if self.debug:
      try:
        psutil_process = psutil.Process(promise_process.pid)
        ps_profile = True
      except psutil.NoSuchProcess:
        # process is gone
        pass
    for current_increment in range(0, increment_limit):
      if not promise_process.is_alive():
        try:
          queue_item = self.queue_result.get(True, 1)
        except Queue.Empty:
          # no result found in process result Queue
          pass
        else:
          queue_item.execution_time = execution_time
        break

      if ps_profile:
        try:
          io_counter = psutil_process.io_counters()
          self.logger.debug(
            "[t=%ss] CPU: %s%%, MEM: %s MB (%s%%), DISK: %s Read - %s Write" % (
              current_increment*sleep_time,
              psutil_process.cpu_percent(),
              psutil_process.memory_info().rss / float(2 ** 20),
              round(psutil_process.memory_percent(), 4),
              io_counter.read_count,
              io_counter.write_count
            )
          )
        except (psutil.AccessDenied, psutil.NoSuchProcess):
          # defunct process will raise AccessDenied
          pass
      time.sleep(sleep_time)
      execution_time = (current_increment + 1) * sleep_time
    else:
      promise_process.terminate()
      promise_process.join(1) # wait for process to terminate
      # if the process is still alive after 1 seconds, we kill it
      if promise_process.is_alive():
        self.logger.info("Killing process %s..." % promise_name)
        killProcessTree(promise_process.pid, self.logger)

      message = 'Error: Promise timed out after %s seconds' % self.promise_timeout
      queue_item = self._generatePromiseResult(
        promise_process,
        promise_name=promise_name,
        promise_path=promise_path,
        message=message,
        execution_time=execution_time
      )

    if queue_item is None:
      queue_item = self._generatePromiseResult(
        promise_process,
        promise_name=promise_name,
        promise_path=promise_path,
        message="Error: No output returned by the promise",
        execution_time=execution_time
      )

    if not self.dry_run:
      self._savePromiseResult(queue_item)
    if queue_item.item.hasFailed():
      self.logger.error(queue_item.item.message)
      if isinstance(queue_item.item, AnomalyResult) and self.check_anomaly:
        # stop to bang as it was called
        self.bang_called = True

    if self.debug:
      self.logger.debug("Finished promise %r in %s second(s)." % (
                       promise_name, execution_time))

    return queue_item.item.hasFailed()

  def run(self):
    """
      Run all promises
    """
    promise_list = []
    failed_promise_name = ""
    base_config = {
      'log-folder': self.log_folder,
      'partition-folder': self.partition_folder,
      'debug': self.debug,
      'promise-timeout': self.promise_timeout,
      'master-url': self.master_url,
      'partition-cert': self.partition_cert,
      'partition-key': self.partition_key,
      'partition-id': self.partition_id,
      'computer-id': self.computer_id,
      'queue': self.queue_result,
    }

    if os.path.exists(self.promise_folder) and os.path.isdir(self.promise_folder):
      for promise_name in os.listdir(self.promise_folder):
        if promise_name.startswith('__init__') or \
            not promise_name.endswith('.py'):
          continue

        if self.run_only_promise_list is not None and not \
            promise_name in self.run_only_promise_list:
          continue

        promise_path = os.path.join(self.promise_folder, promise_name)
        config = {
          'path': promise_path,
          'name': promise_name
        }

        config.update(base_config)
        if self._launchPromise(promise_name, promise_path, config) and \
            not failed_promise_name:
          failed_promise_name = promise_name

    if not self.run_only_promise_list and os.path.exists(self.legacy_promise_folder) \
        and os.path.isdir(self.legacy_promise_folder):
      # run legacy promise styles
      for promise_name in os.listdir(self.legacy_promise_folder):
        promise_path = os.path.join(self.legacy_promise_folder, promise_name)
        if not os.path.isfile(promise_path) or \
            not os.access(promise_path, os.X_OK):
          self.logger.warning("Bad promise file at %r." % promise_path)
          continue

        config = {
          'path': promise_path,
          'name': promise_name
        }
        config.update(base_config)
        # We will use promise wrapper to run this
        result_state = self._launchPromise(promise_name,
                                           promise_path,
                                           config,
                                           wrap_process=True)
        if result_state and not failed_promise_name:
          failed_promise_name = promise_name

    self._updateFolderOwner(self.promise_output_dir)

    if failed_promise_name:
      raise PromiseError("Promise %r failed." % failed_promise_name)
