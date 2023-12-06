import slapos.testing.e2e as e2e

class HealthTest(e2e.EndToEndTestCase):
  instance_name = e2e.time.strftime('e2e-test-health-%Y-%B-%d-%H:%M:%S')

  @classmethod
  def setupInstance(cls):
    parameter_dict = {}
    json_in_xml_parameters = {'_': json.dumps(parameter_dict)}
    cls.partition = cls.request(
      cls.product.slapmonitor,
      cls.instance_name,
      partition_parameter_kw=json_in_xml_parameters,
      software_type='default'
    )
    cls.waitUntilGreen(instance_name)
    cls.connection_dict = cls.getInstanceInfos(instance_name).connection_dict

  def test_health_promise_feed(self):
    resp, url = self.waitUntilMonitorURLReady(instance_name=self.instance_name)
    self.getMonitorPromises(resp.content)
