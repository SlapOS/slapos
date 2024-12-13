import itertools
import json
import logging
import os
import re

from dateutil import parser as dateparser
from datetime import datetime

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

def iter_reverse_lines(f):
  """
    Read lines from the end of the file
  """
  f.seek(0, os.SEEK_END)
  while True:
    try:
      while f.seek(-2, os.SEEK_CUR) and f.read(1) != b'\n':
        pass
    except OSError:
      return
    pos = f.tell()
    yield f.readline()
    f.seek(pos, os.SEEK_SET)


def iter_logrotate_file_handle(path, mode='r'):
  """
    Yield successive file handles for rotated logs
    (XX.log, XX.log.1, XX.log.2, ...)
  """
  for i in itertools.count():
    path_i = path + str(i or '')
    try:
      with open(path_i, mode) as f:
        yield f
    except OSError:
      break

def get_json_log_data_interval(json_log_file, interval):
  """
    Get all data in the last "interval" seconds from JSON log
    Reads rotated logs too (XX.log, XX.log.1, XX.log.2, ...)
  """
  current_time = datetime.now()
  data_list = []
  for f in iter_logrotate_file_handle(json_log_file, 'rb'):
    for line in iter_reverse_lines(f):
      l = json.loads(line)
      timestamp = dateparser.parse(l['time'])
      if (current_time - timestamp).total_seconds() > interval:
        return data_list
      data_list.append(l['data'])
  return data_list

class JSONPromise(GenericPromise):
  def __init__(self, config):
    self.__name = config.get('name', None)
    self.__log_folder = config.get('log-folder', None)

    super(JSONPromise, self).__init__(config)
    json_log_name = os.path.splitext(self.__name)[0] + '.json.log'
    self.__json_log_file = os.path.join(self.__log_folder, json_log_name)
    self.json_logger = self.__make_json_logger(self.__json_log_file)

  def __make_json_logger(self, json_log_file):
    logger = logging.getLogger('json-logger')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(json_log_file)
    formatter = logging.Formatter(
      '{"time": "%(asctime)s", "log_level": "%(levelname)s"'
      ', "message": "%(message)s", "data": %(data)s}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

@implementer(interface.IPromise)
class RunPromise(JSONPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=1)
    self.amarisoft_rf_info_log = self.getConfig('amarisoft-rf-info-log')
    self.stats_period = int(self.getConfig('stats-period'))

  def sense(self):

      data_list = get_json_log_data_interval(self.amarisoft_rf_info_log, self.stats_period * 2)
      if len(data_list) < 1:
        self.logger.error("rf_info: stale data")
        return

      rf_info_text = data_list[0]['rf_info']

      if 'Sync: gps (locked)' in rf_info_text:
        self.logger.info("GPS locked")
      else:
        self.logger.error("GPS not locked")


  def test(self):
    """
      Called after sense() if the instance is still converging.
      Returns success or failure based on sense results.

      In this case, fail if the previous sensor result is negative.
    """
    return self._test(result_count=1, failure_amount=1)


  def anomaly(self):
    """
      Called after sense() if the instance has finished converging.
      Returns success or failure based on sense results.
      Failure signals the instance has diverged.

      In this case, fail if two out of the last three results are negative.
    """
    return self._anomaly(result_count=1, failure_amount=1)
