import pathlib
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  pathlib.Path(__file__).parent.parent / "software.cfg")


class TestMosquitto(SlapOSInstanceTestCase):
  """
  Test if mosquitto service can publish and subscribe
  to specific topics with custom authentication ...
  """

  def test_ipv4(self):
    self._test(self.computer_partition.getConnectionParameterDict()["ipv4"])

  def test_ipv6(self):
    self._test(self.computer_partition.getConnectionParameterDict()["ipv6"])

  def _test(self, host):
    username = self.computer_partition.getConnectionParameterDict()["username"]
    password = self.computer_partition.getConnectionParameterDict()["password"]
    port = int(self.computer_partition.getConnectionParameterDict()["port"])

    topic = "test"
    payload = "Hello, World!"

    client = mqtt.Client()
    client.enable_logger(self.logger)

    def on_connect(client, userdata, flags, rc):
      client.subscribe(topic)

    client.on_connect = on_connect

    def on_subscribe(client, userdata, mid, granted_qos, properties=None):
      # once our client is subscribed, publish from another connection
      publish.single(
        topic=topic,
        payload=payload,
        hostname=host,
        auth={"username": username, "password": password},
      )

    client.on_subscribe = on_subscribe

    def on_message(client, userdata, msg):
      self.topic = msg.topic
      self.payload = str(msg.payload.decode())

    client.on_message = on_message

    client.username_pw_set(username=username, password=password)
    client.connect(host, port)

    self.topic = None  # will be set by on_message
    max_retries = 100  # give up after this number of iterations
    for _ in range(max_retries):
      client.loop()
      if self.topic is not None:
        break

    self.assertEqual(self.topic, topic)
    self.assertEqual(self.payload, payload)
