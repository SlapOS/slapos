import os
import errno
import subprocess

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):

    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=1)


  def sense(self):

    testing = self.getConfig('testing') == "True"
    sdr = self.getConfig('sdr')

    if testing:
        self.logger.info("skipping promise")
        return
    try:
      out = subprocess.check_output([
        sdr + '/sdr_util', '-c', '0', 'version'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      if e.returncode == 1 and \
        ("DMA channel is already opened" in e.output.decode() or \
         "Device or resource busy" in e.output.decode()):
        self.logger.info("eNB is using /dev/sdr0")
        return
    self.logger.error("eNB is not using /dev/sdr0")


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
