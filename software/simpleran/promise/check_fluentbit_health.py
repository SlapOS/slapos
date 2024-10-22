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

    forward_host = self.getConfig('forward-host')
    monitoring_host = self.getConfig('monitoring-host')
    monitoring_port = self.getConfig('monitoring-port')
    health_api_endpoint = '/api/v1/health'

    if not (monitoring_host and monitoring_port):
      self.logger.error("Monitoring server address must be specified with host and port")
      return

    # Check forward host validity first
    if not forward_host:
      self.logger.error("Fluentbit forward host unspecified")
      return
    else:
      try:
        forward_host_response = requests.options(forward_host)
      except requests.exceptions.RequestException:
        self.logger.error("Fluentbit forward host unreachable: %s", forward_host)
        return

    monitoring_url = "http://%s:%s%s" % (monitoring_host, monitoring_port, health_api_endpoint)
    try:
      monitoring_response = requests.get(monitoring_url)

      monitoring_status_code = monitoring_response.status_code 
      monitoring_message = monitoring_response.text.strip()

      if monitoring_status_code == 200 and monitoring_message == 'ok':
        self.logger.info("Fluentbit service is OK")
      elif monitoring_status_code == 500 and monitoring_message == 'error':
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

