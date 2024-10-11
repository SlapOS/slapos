import os
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "software.cfg"))
)


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

    topic = "test"
    payload = "Hello, World!"

    client = mqtt.Client()
    client.enable_logger(self.logger)

    def on_connect(client, userdata, flags, rc):
      client.subscribe(topic)
      self.code = rc

    client.on_connect = on_connect

    def on_subscribe(client, userdata, mid, granted_qos, properties=None):
      self.subscribed = True

    client.on_subscribe = on_subscribe

    def on_message(client, userdata, msg):
      self.topic = msg.topic
      self.payload = str(msg.payload.decode())

    client.on_message = on_message

    client.username_pw_set(username=username, password=password)
    client.connect(host, 1883, 10)
    self.subscribed = False  # will be set by on_subscribe
    for _ in range(100):
      client.loop()
      if self.subscribed:
        break

    publish.single(
      topic=topic,
      payload=payload,
      hostname=host,
      auth={"username": username, "password": password},
    )
    self.topic = None  # will be set by on_message
    for _ in range(100):
      client.loop()
      if self.topic is not None:
        break

    self.assertEqual(self.code, 0)
    self.assertEqual(self.topic, topic)
    self.assertEqual(self.payload, payload)
