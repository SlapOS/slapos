from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import json
import requests

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=1)
    self.result_count = int(self.getConfig('result-count', 3))
    self.failure_amount = int(self.getConfig('failure-amount', 3))
    self.testing = self.getConfig('testing') == "True"


  def sense(self):
    if self.testing:
      self.logger.info("Testing: skipping promise")
      return

    host = self.getConfig('host')
    port = self.getConfig('port')
    health_api_endpoint = '/api/v1/health'

    if not (host and port):
      self.logger.error("Address must be specified with host and port")
      return

    url = "http://%s:%s%s" % (host, port, health_api_endpoint)

    try:
      response = requests.get(url)

      status_code = response.status_code 
      response_message = response.text.strip()

      if status_code == 200 and response_message == 'ok':
        self.logger.info("Fluentbit service is OK")
      elif status_code == 500 and response_message == 'error':
        self.logger.error("Fluentbit output to forward host is failing")
      else:
        self.logger.error("Error encountered in Fluentbit monitoring API")
    except requests.exceptions.RequestException:
      self.logger.error("Fluentbit service has exited")


  def anomaly(self):
    """
      By default, there is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=self.result_count, failure_amount=self.failure_amount)

