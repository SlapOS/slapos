import socket
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
    self.setPeriodicity(minute=2)


  def sense(self):
    """
      Called every time the promise is tested.
      Signals a positive or negative result.

      In this case, check whether the file exists.
    """
    ifname = self.getConfig('ifname')
    testing = self.getConfig('testing')

    if testing:
        self.logger.info("skipping promise")
        return

    f = open('/sys/class/net/%s/operstate' % ifname, 'r')
    if f.read() == 'up\n':
      self.logger.info("%s is up", ifname)
    else:
      self.logger.error("%s is down", ifname)
    f.close()

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
