import e2e

class HealthTest(e2e.EndToEndTestCase):
  # instance_name = time.strftime('e2e-test-kvm-%Y-%B-%d-%H:%M:%S')
  instance_name = 'cb006-health' # avoid timestamp to reuse instance

  @classmethod
  def setupInstance(cls):
    monitor_sr_url = "https://lab.nexedi.com/nexedi/slapos/raw/1.0.341/software/monitor/software.cfg"
    parameter_dict = {}
    json_in_xml_parameters = {'_': json.dumps(parameter_dict)}
    cls.partition = cls.request(
      monitor_sr_url,
      cls.instance_name,
      partition_parameter_kw=json_in_xml_parameters,
      software_type='default'
    )
    cls.waitUntilGreen(instance_name)
    cls.connection_dict = cls.getInstanceInfos(instance_name).connection_dict

  def test_health_promise_feed(self):
    resp, url = self.waitUntilMonitorURLReady(instance_name=self.instance_name)
    self.getMonitorPromises(resp.content)

