import errno
import json
import logging
import os

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
    self.setPeriodicity(minute=1)

    self.__title = os.path.splitext(self.__name)[0]
    self.__log_file = os.path.join(self.__log_folder, '%s.json.log' % self.__title)

    self.json_logger = logging.getLogger('json_logger')
    self.json_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(self.__log_file)
    formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
    handler.setFormatter(formatter)
    self.json_logger.addHandler(handler)

  def sense(self):

    testing = self.getConfig('testing') == "True"
    amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    stats_period = int(self.getConfig('stats-period'))
    max_rx_sample_db = float(self.getConfig('max-rx-sample-db'))

    data_list = get_data_interval(amarisoft_stats_log, stats_period * 2)

    max_rx = []
    saturated = False

    for data in data_list:
        rx_list = data['samples']['rx']
        if not max_rx:
            max_rx = [-99.9 for x in rx_list]
        for i, rx in enumerate(rx_list):
            max_rx[i] = max(max_rx[i], float(rx['max']))
            if max_rx[i] >= max_rx_sample_db:
                saturated = True

    self.json_logger.info("RX maximum sample values (dB)",
      extra={'data': max_rx})

    if not max_rx:
        self.logger.error("No RX samples data available")
    elif saturated:
        self.logger.error("RX antenna saturated, please lower rx_gain")
    else:
        self.logger.info("No saturation detected on RX antenna")

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
