import e2e

class KvmTest(e2e.EndToEndTestCase):
  def test(self):
    instance_name = e2e.time.strftime('e2e-test-kvm-%Y-%B-%d-%H:%M:%S')
    # instance_name = 'e2e-kvm-test' # avoid timestamp to reuse instance
    self.request(self.product.kvm, instance_name)
    self.waitUntilGreen(instance_name)
    connection_dict = self.request(self.product.kvm, instance_name)
    self.assertIn('url', connection_dict)
