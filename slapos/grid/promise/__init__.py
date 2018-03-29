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
from slapos.grid.utils import dropPrivileges
from slapos.grid.promise import interface
from slapos.grid.promise.generic import (GenericPromise, PromiseQueueResult,
                                         AnomalyResult, TestResult,
                                         PROMISE_RESULT_FOLDER_NAME)
from slapos.grid.promise.wrapper import WrapPromise


class PromiseError(Exception):
  pass

class PromiseRunner(Process):

  """
    Run a promise in a new Process
  """

  def __init__(self, promise_instance, logger=None, allow_bang=True, uid=None,
      gid=None, cwd=None, check_anomaly=False):
    """
      Initialise Promise Runner

      @param promise_instance: Promise instance from GenericPromise class
      @param allow_bang: Bolean saying if bang should be called in case of
        anomaly failure.
    """
    Process.__init__(self)
    self.promise = promise_instance
    self.logger = logger
    self.allow_bang = allow_bang
    self.check_anomaly = check_anomaly
    self.uid = uid
    self.gid = gid
    self.cwd = cwd

  def run(self):
    if self.uid and self.gid:
      dropPrivileges(self.uid, self.gid, logger=self.logger)
    if self.cwd is not None:
      os.chdir(self.cwd)
    try:
      self.promise.run(self.check_anomaly, self.allow_bang)
    except Exception, e:
      if self.logger:
        self.logger.error(str(e))
      raise


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

  def _loadPromiseModule(self, promise_name):
    """Load a promise from promises directory."""

    if re.match(r'[a-zA-Z_]', promise_name) is None:
      self.logger.error("Promise plugin name %r is not valid" % promise_name)

    promise_module = importlib.import_module(os.path.splitext(promise_name)[0])
    if not hasattr(promise_module, "RunPromise"):
      raise AttributeError("Class RunPromise not found in promise" \
        "%s" % promise_name)
    if not interface.IPromise.implementedBy(promise_module.RunPromise):
      raise RuntimeError("RunPromise class in %s must implements 'IPromise'" \
        " interface. zope_interface.implements(interface.IPromise) is" \
        " missing ?" % promise_name)
    if not issubclass(promise_module.RunPromise, GenericPromise):
      raise RuntimeError("RunPromise class is not a subclass of" \
        "GenericPromise class.")

    return promise_module

  def _getErrorPromiseResult(self, promise_instance, promise_name, message,
      execution_time=0):
    if self.check_anomaly:
      result = AnomalyResult(problem=True, message=message)
    else:
      result = TestResult(problem=True, message=message)
    return PromiseQueueResult(
      item=result,
      path=os.path.join(self.promise_folder, promise_name),
      name=promise_name,
      title=promise_instance.getTitle(),
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

  def _launchPromise(self, promise_name, argument_dict, promise_module=None):
    """
      Launch the promise and save the result. If promise_module is None,
      the promise will be run with the promise process wap module.

      If the promise periodicity doesn't match, the previous promise result is
      checked.
    """
    self.logger.info("Checking promise %s..." % promise_name)
    try:
      if promise_module is None:
        promise_instance = WrapPromise(argument_dict)
      else:
        promise_instance = promise_module.RunPromise(argument_dict)
      if not self.force and not promise_instance.isPeriodicityMatch():
        result = self._loadPromiseResult(promise_instance.getTitle())
        if result is not None:
          if result.item.hasFailed():
            self.logger.error(result.item.message)
            return True
        return False
      promise_instance.setPromiseRunTimestamp()
    except Exception:
      # only print traceback to not prevent run other promises
      self.logger.error(traceback.format_exc())
      self.logger.warning("Promise %s skipped." % promise_name)
      return True

    promise_process = PromiseRunner(
      promise_instance,
      check_anomaly=self.check_anomaly,
      allow_bang=not (self.bang_called or self.dry_run) and self.check_anomaly,
      uid=self.uid,
      gid=self.gid,
      cwd=self.partition_folder,
      logger=self.logger
    )

    # set deamon to True, so promise process will be terminated if parent exit
    promise_process.daemon = True
    promise_process.start()

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
      promise_process.join() # wait for process to terminate
      message = 'Promise timed out after %s seconds' % self.promise_timeout
      queue_item = self._getErrorPromiseResult(
        promise_instance,
        promise_name=promise_name,
        message=message,
        execution_time=execution_time
      )

    if queue_item is None:
      queue_item = self._getErrorPromiseResult(
        promise_instance,
        promise_name=promise_name,
        message="No output returned by the promise",
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
      # if there is no __init__ file, add it
      init_file = os.path.join(self.promise_folder, '__init__.py')
      if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
          f.write("")
        os.chmod(init_file, 0644)
      if sys.path[0] != self.promise_folder:
        sys.path[0:0] = [self.promise_folder]

      promise_list = []
      # load all promises so we can catch import errors before launch them
      for promise_name in os.listdir(self.promise_folder):
        if promise_name.startswith('__init__') or \
            not promise_name.endswith('.py'):
          continue
        if self.run_only_promise_list is not None and not \
            promise_name in self.run_only_promise_list:
          continue
        promise_list.append((promise_name,
                             self._loadPromiseModule(promise_name)))

      for name, module in promise_list:
        promise_path = os.path.join(self.promise_folder, name)
        config = {
          'path': promise_path,
          'name': name
        }
        if module.__file__ != promise_path:
          # cached module need to be updated
          module = reload(module)

        config.update(base_config)
        if self._launchPromise(name, config, module) and not failed_promise_name:
          failed_promise_name = name

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
        if self._launchPromise(promise_name, config) and not failed_promise_name:
          failed_promise_name = promise_name

    stat_info = os.stat(self.partition_folder)
    chownDirectory(self.partition_folder, stat_info.st_uid, stat_info.st_gid)

    if failed_promise_name:
      raise PromiseError("Promise %r failed." % failed_promise_name)
