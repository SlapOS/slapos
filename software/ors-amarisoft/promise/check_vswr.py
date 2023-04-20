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
    if testing:
        self.logger.info("skipping promise")
        return
    lopcomm_stats_log = self.getConfig('lopcomm-stats-log')
    data_list = get_data_interval(lopcomm_stats_log, 120)

#    fault_texts = []
# Example of data_list
#('[\n'
# '    {\n'
# '        "notification": {\n'
# '            "@xmlns": "urn:ietf:params:xml:ns:netconf:notification:1.0",\n'
# '            "eventTime": "1970-01-05T00:38:50Z",\n'
# '            "alarm-notif": {\n'
# '                "@xmlns": "urn:o-ran:fm:1.0",\n'
# '                "fault-id": "9",\n'
# '                "fault-source": "Antport1",\n'
# '                "affected-objects": {\n'
# '                    "name": "Antport1"\n'
# '                },\n'
# '                "fault-severity": "MAJOR",\n'
# '                "is-cleared": "false",\n'
# '                "fault-text": "PA 1 VSWR Alarm",\n'
# '                "event-time": "1970-01-05T00:38:50Z"\n'
# '            }\n'
# '        }\n'
# '    },\n'
# ']')
    fault_text_list = []
    alarm = False

    for data in data_list:
        notifications = data['notification']
        alarm_notifs = notifications['alarm-notif']
        fault_texts = alarm_notifs['fault-text']
        fault_sources = alarm_notifs['fault-source']
        is_cleared = alarm_notifs['is-cleared']

        if not fault_text_list:
            fault_text_list = ["None",]
        for i, fault_text in enumerate(fault_texts):
            if 'VSWR' in fault_text:
                if is_cleared == 'false':
                    alarm = True
                    self.logger.error(fault_sources + ": " +fault_texts)
                else:
                    self.logger.info(fault_sources + ": " +fault_texts + " is no longer over threshold")

    if not data_list:
        self.logger.error("No notification available")
    elif not alarm:
        self.logger.info("No VSWR alarm detected")

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
