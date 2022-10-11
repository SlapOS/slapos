import os
import errno

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise




@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    """
      Called when initialising the promise before testing.
      Sets the configuration and the periodicity.
    """
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=1)


  def sense(self):
    """
      Called every time the promise is tested.
      Signals a positive or negative result.

      In this case, check whether the file exists.
    """
    testing = self.getConfig('testing') == "True"
    sdr_dev = '/dev/sdr0'

    if testing:
        self.logger.info("skipping promise")
        return

    try:
      open(sdr_dev, 'w').close()
      self.logger.error("eNB is not using %s", sdr_dev)
    except IOError as e:
      if e.errno == errno.EBUSY:
        self.logger.info("eNB is using %s", sdr_dev)

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
