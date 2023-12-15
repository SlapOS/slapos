import slapos.testing.e2e as e2e
import time


class HealthTest(e2e.EndToEndTestCase):

  @classmethod
  def test_health_promise_feed(self):
    instance_name = e2e.time.strftime('e2e-test-health-%Y-%B-%d-%H:%M:%S')
    product = self.product.slapmonitor
    parameter_dict = {}
    self.request(
      self.product.slapmonitor,
      instance_name,
      software_type='default',
      filter_kw={"computer_guid": "COMP-4057"})
    self.waitUntilGreen(instance_name)
    self.connection_dict = self.getInstanceInfos(instance_name).connection_dict

    resp, url = self.waitUntilMonitorURLReady(instance_name=instance_name)
    self.getMonitorPromises(resp.content)
