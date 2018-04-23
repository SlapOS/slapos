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
import logging
import re
import time
import random
import traceback
import slapos.slap
from slapos.util import mkdir_p
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta

PROMISE_STATE_FOLDER_NAME = '.slapgrid/promise'
PROMISE_RESULT_FOLDER_NAME = '.slapgrid/promise/result'
PROMISE_LOG_FOLDER_NAME = '.slapgrid/promise/log'

PROMISE_PARAMETER_NAME = 'extra_config_dict'
PROMISE_PERIOD_FILE_NAME = '%s.periodicity'

class BaseResult(object):
  def __init__(self, problem=False, message=None, date=None):
    self.__problem = problem
    # The promise message should be very short,
    # a huge message size can freeze the process Pipe
    # XXX this is important to prevent process deadlock
    if len(message) > 5000:
      message = '...%s' % message[-5000:]
    self.__message = message
    self.__date = date
    if self.__date is None:
      self.__date = datetime.utcnow()

  def hasFailed(self):
    return self.__problem

  @staticmethod
  def type():
    return "Base Result"

  @property
  def message(self):
    return self.__message

  @property
  def date(self):
    return self.__date

class TestResult(BaseResult):

  @staticmethod
  def type():
    return "Test Result"

class AnomalyResult(BaseResult):

  @staticmethod
  def type():
    return "Anomaly Result"

class PromiseQueueResult(object):

  def __init__(self, path=None, name=None, title=None,
               item=None, execution_time=0):
    self.path = path
    self.name = name
    self.item = item
    self.title = title
    self.execution_time = execution_time

  def serialize(self):
    return {
      'title': self.title,
      'name': self.name,
      'path': self.path,
      'execution-time': self.execution_time,
      'result': {
        'type': self.item.type(),
        'failed': self.item.hasFailed(),
        'date': self.item.date.strftime('%Y-%m-%dT%H:%M:%S'),
        'message': self.item.message
      }
    }

  def load(self, data):
    if data['result']['type'] == AnomalyResult.type():
      self.item = AnomalyResult(
        problem=data['result']['failed'],
        message=data['result']['message'],
        date=datetime.strptime(data['result']['date'], '%Y-%m-%dT%H:%M:%S'))
    elif data['result']['type'] == TestResult.type():
      self.item = TestResult(
        problem=data['result']['failed'],
        message=data['result']['message'],
        date=datetime.strptime(data['result']['date'], '%Y-%m-%dT%H:%M:%S'))
    else:
      raise ValueError('Unknown result type: %r' % data['result']['type'])

    self.title = data['title']
    self.name = data['name']
    self.path = data['path']
    self.execution_time = data['execution-time']

class GenericPromise(object):

  # Abstract class
  __metaclass__ = ABCMeta

  def __init__(self, config):
    self.__config = config

    self.__log_folder = self.__config.pop('log-folder', None)
    self.__partition_folder = self.__config.pop('partition-folder', None)
    self.__debug = self.__config.pop('debug', True)
    self.__name = self.__config.pop('name', None)
    self.__promise_path = self.__config.pop('path', None)
    self.__queue = self.__config.pop('queue', None)
    self.__logger_buffer = None
    self.__periodicity_file = os.path.join(
      self.__partition_folder,
      PROMISE_STATE_FOLDER_NAME,
      PROMISE_PERIOD_FILE_NAME % self.__name)
    self.setPeriodicity(self.__config.pop('periodicity', 2))

    self.__transaction_id = '%s-%s' % (int(time.time()), random.randint(100, 999))

    self._validateConf()
    self._configureLogger()

  def _configureLogger(self):
    self.logger = logging.getLogger(self.__name)
    for handler in self.logger.handlers:
      self.logger.removeHandler(handler)
    if self.__log_folder is None:
      # configure logger with StringIO
      import cStringIO
      self.__logger_buffer = cStringIO.StringIO()
      logger_handler = logging.StreamHandler(self.__logger_buffer)
      self.__log_file = None
    else:
      mkdir_p(self.__log_folder)
      self.__log_file = os.path.join(
        self.__log_folder,
        '%s.log' % self.__title
      )
      logger_handler = logging.FileHandler(self.__log_file)

    self.logger.setLevel(logging.DEBUG if self.__debug else logging.INFO)
    logger_handler.setFormatter(
      fmt=logging.Formatter("%(asctime)s - %(levelname)s - " +
          self.__transaction_id + " - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    )
    self.logger.addHandler(logger_handler)

  def _validateConf(self):
    if self.__queue is None:
      raise ValueError("Queue object is not set in configuration")
    if self.__name is None:
      raise ValueError("Monitor name is not set in configuration")
    self.__title = os.path.splitext(self.__name)[0]
    if self.__promise_path is None:
      raise ValueError("Promise path is not set in configuration")
    if self.__partition_folder is None:
      raise ValueError("Monitor partition folder is not set in configuration")

  def getConfig(self, key, default=None):
    return self.__config.get(key, default)

  def setConfig(self, key, value):
    self.__config[key] = value

  def getTitle(self):
    return self.__title

  def getName(self):
    return self.__name

  def getLogFile(self):
    return self.__log_file

  def getLogFolder(self):
    return self.__log_folder

  def getPartitionFolder(self):
    return self.__partition_folder

  def getPromiseFile(self):
    return self.__promise_path

  def setPeriodicity(self, minute):
    if minute <= 0:
      raise ValueError("Cannot set promise periodicity to a value less than 1")
    self.__periodicity = minute
    with open(self.__periodicity_file, 'w') as f:
      f.write('%s' % minute)

  def getPeriodicity(self):
    return self.__periodicity

  def __bang(self, message):
    """
      Call bang if requested
    """
    if self.__config.has_key('master-url') and \
        self.__config.has_key('partition-id') and \
        self.__config.has_key('computer-id'):

      slap = slapos.slap.slap()
      slap.initializeConnection(
          self.__config['master-url'],
          self.__config.get('partition-key'),
          self.__config.get('partition-cert'),
      )
      computer_partition = slap.registerComputerPartition(
          self.__config['computer-id'],
          self.__config['partition-id'],
      )
      computer_partition.bang(message)
      self.logger.info("Bang with message %r." % message)

  def __getLogRegex(self):
    return re.compile(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\-?\s*(\w{4,7})\s+\-?\s+(\d+\-\d{3})\s+\-?\s*(.*)")

  def __getResultFromString(self, result_string, only_failure=False):
    line_list = result_string.split('\n')
    result_list = []
    line_part = ""
    regex = self.__getLogRegex()
    for line in line_list:
      if not line:
        continue
      match = regex.match(line)
      if match is not None:
        if not only_failure or (only_failure and match.groups()[1] == 'ERROR'):
          result_list.append({
            'date': datetime.strptime(match.groups()[0], '%Y-%m-%d %H:%M:%S'),
            'status': match.groups()[1],
            'message': (match.groups()[3] + line_part).strip(),
          })
        line_part = ""
      else:
        line_part += '\n' + line
    result_list

    return [result_list]

  def getLastPromiseResultList(self, latest_minute=0, result_count=1,
      only_failure=False):
    """
      Return the latest log result of the promise starting from the most recent

      @param last_minute: the number of minutes in the past. If last_minute is
        1, it will return the log of the latest minute execution. 0 => disabled
      @param only_failure: only return the lines which contain failures.
      @param result_count: maximum number of promise result to check, will not
        exceed the `latest_minute`
      @return Return a list of logs. The format is
        [[{"date": "DATE", "status": "STATUS", "message": MESSAGE}, ...], ...]
    """

    if self.__log_file is None:
      if self.__logger_buffer is not None:
        return self.__getResultFromString(self.__logger_buffer.getvalue(),
                                          only_failure)
      else:
        return []

    if not os.path.exists(self.__log_file):
      return []

    regex = self.__getLogRegex()
    max_date_string = ""
    if latest_minute > 0:
      date = datetime.now() - timedelta(minutes=latest_minute)
      max_date_string = date.strftime('%Y-%m-%d %H:%M:%S')

    line_list = []
    result_list = []
    transaction_id = None
    transaction_count = 0
    with open(self.__log_file, 'r') as f:
      offset = 0
      f.seek(0, 2)
      size = f.tell() * -1
      line = line_part = ""
      while offset > size:
        offset -= 1
        f.seek(offset, 2)
        char = f.read(1)
        if char != '\n':
          line = char + line
        if char == '\n' or offset == size:
          # Add new line
          if offset == -1:
            continue
          if line != "":
            result = regex.match(line)
            if result is not None:
              if max_date_string and result.groups()[0] <= max_date_string:
                break
              if transaction_id != result.groups()[2]:
                if transaction_id is not None:
                  # append new result
                  result_list.append(line_list)
                  line_list = []
                transaction_count += 1
                if transaction_count > result_count:
                  break
                transaction_id = result.groups()[2]
              if not only_failure or \
                  (only_failure and result.groups()[1] == 'ERROR'):
                line_list.insert(0, {
                  'date': datetime.strptime(result.groups()[0],
                                            '%Y-%m-%d %H:%M:%S'),
                  'status': result.groups()[1],
                  'message': (result.groups()[3] + line_part).strip(),
                })
            else:
              line_part = '\n' + line + line_part
              line = ""
              continue
            line = line_part = ""

    if len(line_list):
      result_list.append(line_list)
    return result_list

  def __readResultList(self, result_list):
    failed = False
    message = ""
    for result in result_list:
      if result['status'] == 'ERROR':
        failed = True
      message += "\n%s" % result['message']
    return failed, message.strip()

  def __checkPromiseResult(self, result_count=1, failure_amount=1,
      latest_minute=0, is_anomaly=False):
    """
      Test if the latest messages contain `failure_amount` failures.

      @param result_count: maximum number of promise result to check, will not
        exceed the `latest_minute`
      @param latest_minute: test the result from now to the latest X minutes in
        the past.
      @param failure_amount: fail is this amount of failure is found in result
      @param is_anomaly: Say if the result is an AnomalyResult of TestResult
    """

    module = TestResult if not is_anomaly else AnomalyResult
    latest_result_list = self.getLastPromiseResultList(
      result_count=result_count,
      latest_minute=latest_minute,
      only_failure=False
    )
    result_size = len(latest_result_list)
    if result_size == 0:
      return module(problem=False, message="No result found!")
    problem, message = self.__readResultList(latest_result_list[0])
    if not problem:
      # latest execution is OK
      return module(problem=False, message=message)

    i = 1
    failure_found = 1
    while i < result_size and failure_found < failure_amount:
      for result in latest_result_list[i]:
        if result['status'] == 'ERROR':
          failure_found += 1
          break
      i += 1

    if failure_found != failure_amount:
      return module(problem=False, message=message)
    return module(problem=True, message=message)

  def __sendResult(self, result_item, retry_amount=3):
    """Send result to queue, retry if error (non blocking)"""
    error = None
    for i in range(0, retry_amount):
      try:
        self.__queue.put_nowait(result_item)
        break
      except Queue.Full, e:
        error = e
        time.sleep(0.5)
    if error:
      raise error

  def _test(self, result_count=1, failure_amount=1, latest_minute=0):
    """
      Default promise test method
    """
    return self.__checkPromiseResult(
      result_count=result_count,
      failure_amount=failure_amount,
      latest_minute=latest_minute,
      is_anomaly=False
    )

  def _anomaly(self, result_count=1, failure_amount=1, latest_minute=0):
    """
      Default anomaly check method
    """
    return self.__checkPromiseResult(
      result_count=result_count,
      failure_amount=failure_amount,
      latest_minute=latest_minute,
      is_anomaly=True
    )

  @abstractmethod
  def sense(self):
    """Run the promise code and log the result"""

  def anomaly(self):
    """Called to detect if there is an anomaly which require to bang."""
    return self._anomaly()

  def test(self):
    """Test promise and say if problem is detected or not"""
    return self._test()

  def run(self, check_anomaly=False, can_bang=True):
    """
      Method called to run the Promise
      @param check_anomaly: Say if anomaly method should be called
      @param can_bang: Set to True if bang can be called, this parameter should
        be set to False if bang is already called by another promise.
    """
    try:
      self.sense()
    except Exception, e:
      # log the result
      self.logger.error(str(e))
    if check_anomaly:
      # run sense, anomaly
      try:
        result = self.anomaly()
        if result is None:
          raise ValueError("Promise anomaly method returned 'None'")
      except Exception, e:
        result = AnomalyResult(problem=True, message=str(e))
      else:
        if isinstance(result, AnomalyResult) and result.hasFailed() and can_bang:
          try:
            self.__bang("Promise %s is failing" % self.__title)
          except:
            self.logger.warning(traceback.format_exc())
    else:
      # run sense, test
      try:
        result = self.test()
        if result is None:
          raise ValueError("Promise test method returned 'None'")
      except Exception, e:
        result = TestResult(problem=True, message=str(e))

    if self.__logger_buffer is not None:
      self.__logger_buffer.close()

    # send the result of this promise
    self.__sendResult(PromiseQueueResult(
      path=self.__promise_path,
      name=self.__name,
      title=self.__title,
      item=result
    ))
