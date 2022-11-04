import errno
import json
import logging
import os
import psutil
import socket
import time

from dateutil import parser

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

# Get all data in the last "interval" seconds from JSON log
def get_data_interval(log, interval):

  log_number = 0
  latest_timestamp = 0
  data_list = []

  while True:
    try:
      f = open("{}.{}".format(log, log_number) if log_number else log, "rb")
    except OSError:
      return data_list
    try:
      f.seek(0, os.SEEK_END)
      while True:
        try:
          while f.seek(-2, os.SEEK_CUR) and f.read(1) != b'\n':
            pass
        except OSError:
          break
        pos = f.tell()
        l = json.loads(f.readline().decode().replace("'", '"'))
        timestamp = parser.parse(l['time'])
        data_list.append(l['data'])
        if not latest_timestamp:
          latest_timestamp = timestamp
        if (latest_timestamp - timestamp).total_seconds() > interval:
          return data_list
        f.seek(pos, os.SEEK_SET)
    finally:
        f.close()
    log_number += 1

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):

    self.__name = config.get('name', None)
    self.__log_folder = config.get('log-folder', None)
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=2)

    self.last_avg_computation_file = self.getConfig(
      'last-avg-computation-file', '')

    self.__title = os.path.splitext(self.__name)[0]
    self.__log_file = os.path.join(self.__log_folder, '%s.json.log' % self.__title)

    self.json_logger = logging.getLogger('json_logger')
    self.json_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(self.__log_file)
    formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": '\
      '"%(levelname)s", "message": "%(message)s", "data": %(data)s}')
    handler.setFormatter(formatter)
    self.json_logger.addHandler(handler)

  def sense(self):

    promise_success = True

    max_spot_temp = float(self.getConfig('max-spot-temp', 90))
    max_avg_temp = float(self.getConfig('max-avg-temp', 80))
    avg_temp_duration = 60 * int(self.getConfig('avg-temp-duration', 5))
    testing = self.getConfig('testing') == "True"

    # Get current temperature
    # TODO: use mock
    if testing:
      from random import randint
      cpu_temp = randint(40, 75)
    else:
      data = psutil.sensors_temperatures()
      cpu_temp = data['coretemp'][0][1]
    if cpu_temp > max_spot_temp:
      self.logger.error("Temperature reached critical threshold: %s degrees "\
        "celsius (threshold is %s degrees celsius)" % (cpu_temp, max_spot_temp))
      promise_success = False

    # Log temperature
    data = json.dumps({'cpu_temperature': cpu_temp})
    self.json_logger.info("Temperature data", extra={'data': data})

    # Computer average temperature
    avg_computation_period = avg_temp_duration / 4
    try:
      t = os.path.getmtime(self.last_avg_computation_file)
    except OSError:
      t = 0
    if (time.time() - t) > avg_computation_period:
      open(self.last_avg_computation_file, 'w').close()
      temp_list = get_data_interval(self.__log_file, avg_temp_duration)
      if temp_list:
        avg_temp = sum(map(lambda x: x['cpu_temperature'], temp_list)) / len(temp_list)
        if avg_temp > max_avg_temp:
          self.logger.error("Average temperature over the last %s seconds "\
            "reached threshold: %s degrees celsius (threshold is %s degrees "\
            "celsius)" % (avg_temp_duration, avg_temp, max_avg_temp))
          promise_success = False
      else:
        self.logger.error("Couldn't read temperature from log")
        promise_success = False

    if promise_success:
      self.logger.info("Temperature OK")

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
    return self._anomaly(result_count=3, failure_amount=2)
