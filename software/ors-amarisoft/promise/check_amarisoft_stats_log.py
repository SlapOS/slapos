import errno
import json
import os

from datetime import datetime
from dateutil import parser

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

# Get latest timestamp from JSON log
def get_latest_timestamp(log):

    log_number = 0

    while True:
        try:
            f = open("{}.{}".format(log, log_number) if log_number else log, "rb")
        except OSError:
            return 0
        try:
            f.seek(0, os.SEEK_END)
            try:
                while f.seek(-2, os.SEEK_CUR) and f.read(1) != b'\n':
                    pass
            except OSError:
                break
            l = json.loads(f.readline().decode().replace("'", '"'))
            return parser.parse(l['time'])
        finally:
            f.close()
        log_number += 1
    return 0

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):

    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=1)

  def sense(self):

    amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    stats_period = int(self.getConfig('stats-period'))

    latest_timestamp = get_latest_timestamp(amarisoft_stats_log)
    delta = (datetime.now() - latest_timestamp).total_seconds()
    if delta > stats_period * 2:
        self.logger.error("Latest entry from amarisoft statistics log too "\
                          "old (%s seconds old)" % (delta,))
    else:
        self.logger.info("Latest entry from amarisoft statistics is "\
                         "%s seconds old" % (delta,))

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
