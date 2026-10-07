from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
    def __init__(self, config):
        super().__init__(config)
        self.setPeriodicity(1)
        self.allowBang(False)
    def sense(self):
        error = self.getConfig('error')
        if not error:
            self.logger.info("No errors during parameter validation")
        else:
            self.logger.error("Invalid parameters: %s", error)
    def test(self):
        return self._test(result_count=1, failure_amount=1)
    def anomaly(self):
        return self._anomaly(result_count=1, failure_amount=1)

