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
    frequency = self.getConfig('frequency')
    range_rating = self.getConfig('range-rating')
    try:
      min_frequency = int(range_rating.split('MHz')[0].strip())
      max_frequency = int(range_rating.split('-')[1].split('MHz')[0].strip())
    except (IndexError, ValueError) as e:
      self.logger.info("Range rating not available, skipping the promise")
      return
    try:
      frequency = int(float(frequency))
    except ValueError as e:
      self.logger.info("Invalid frequency, skipping the promise")
      return

    if min_frequency <= frequency <= max_frequency:
      self.logger.info("Frequency is in bounds ({} MHz <= {} MHz <= {} MHz)".format(
        min_frequency,
        frequency,
        max_frequency))
    elif frequency < min_frequency:
      self.logger.error("Frequency is lower than the lowest possible frequency on this hardware, please increase it ({} MHz < {} MHz)".format(
        frequency,
        min_frequency))
    else:
      self.logger.error("Frequency is higher than the highest possible frequency on this hardware, please increase it ({} MHz > {} MHz)".format(
        frequency,
        max_frequency))
      
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
