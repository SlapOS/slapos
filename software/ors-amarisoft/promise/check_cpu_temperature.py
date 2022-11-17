import socket
import errno
import logging
import json
import os
import psutil

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):

    self.__name = config.get('name', None)
    self.__log_folder = config.get('log-folder', None)

    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=2)

    self.__title = os.path.splitext(self.__name)[0]
    self.__log_file = os.path.join(self.__log_folder, '%s.json.log' % self.__title)

    self.json_logger = logging.getLogger('json_logger')
    self.json_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(self.__log_file)
    formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
    handler.setFormatter(formatter)
    self.json_logger.addHandler(handler)

  def sense(self):

    max_temp = int(self.getConfig('max-temp', 80))
    testing = self.getConfig('testing') == "True"

    if testing:
      from random import randint
      cpu_temp = randint(40, 75)
    else:
      data = psutil.sensors_temperatures()
      cpu_temp = data['coretemp'][0][1]

    data = json.dumps({'cpu_temperature': cpu_temp})
    if cpu_temp > max_temp:
      self.logger.error("Temperature too high (%s > %s)" % (cpu_temp, max_temp))
      self.json_logger.info("Temperature too high (%s > %s)"  % (cpu_temp, max_temp), extra={'data': data})
    else:
      self.logger.info("Temperature OK")
      self.json_logger.info("Temperature OK", extra={'data': data})

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
