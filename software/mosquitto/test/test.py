import os
import time
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

class TestMosquitto(SlapOSInstanceTestCase):

  """
  Test if mosquitto service can publish and subscribe
  to specific topics with custom authentication ...
  """

  def on_connect(self, client, userdata, flags, rc):
    client.subscribe("test")
    self.code = rc

  def on_message(self, client, userdata, msg):
    self.topic = msg.topic
    self.payload = str(msg.payload.decode())

  def test_topic_ipv4(self):
    host = self.computer_partition.getConnectionParameterDict()["ipv4"]
    username = self.computer_partition.getConnectionParameterDict()["username"]
    password = self.computer_partition.getConnectionParameterDict()["password"]

    topic = "test"
    payload = "Hello, World!"

    client = mqtt.Client()
    client.on_connect = self.on_connect
    client.on_message = self.on_message
    client.username_pw_set(username=f"{username}", password=f"{password}")
    client.connect(f"{host}", 1883, 10)

    client.loop_start()

    publish.single(
      topic=topic,
      payload=payload,
      hostname=f"{host}",
      auth={ "username": f"{username}", "password": f"{password}" }
    )

    time.sleep(10)
    client.loop_stop()

    self.assertEqual(self.code, 0)
    self.assertEqual(self.topic, topic)

  def test_payload_ipv4(self):
    host = self.computer_partition.getConnectionParameterDict()["ipv4"]
    username = self.computer_partition.getConnectionParameterDict()["username"]
    password = self.computer_partition.getConnectionParameterDict()["password"]

    topic = "test"
    payload = "Hello, World!"

    client = mqtt.Client()
    client.on_connect = self.on_connect
    client.on_message = self.on_message
    client.username_pw_set(username=f"{username}", password=f"{password}")
    client.connect(f"{host}", 1883, 10)

    client.loop_start()

    publish.single(
      topic=topic,
      payload=payload,
      hostname=f"{host}",
      auth={ "username": f"{username}", "password": f"{password}" }
    )

    time.sleep(10)
    client.loop_stop()

    self.assertEqual(self.code, 0)
    self.assertEqual(self.payload, payload)

  def test_topic_ipv6(self):
    host = self.computer_partition.getConnectionParameterDict()["ipv6"]
    username = self.computer_partition.getConnectionParameterDict()["username"]
    password = self.computer_partition.getConnectionParameterDict()["password"]

    topic = "test"
    payload = "Hello, World!"

    client = mqtt.Client()
    client.on_connect = self.on_connect
    client.on_message = self.on_message
    client.username_pw_set(username=f"{username}", password=f"{password}")
    client.connect(f"{host}", 1883, 10)

    client.loop_start()

    publish.single(
      topic=topic,
      payload=payload,
      hostname=f"{host}",
      auth={ "username": f"{username}", "password": f"{password}" }
    )

    time.sleep(10)
    client.loop_stop()

    self.assertEqual(self.code, 0)
    self.assertEqual(self.topic, topic)

  def test_payload_ipv6(self):
    host = self.computer_partition.getConnectionParameterDict()["ipv6"]
    username = self.computer_partition.getConnectionParameterDict()["username"]
    password = self.computer_partition.getConnectionParameterDict()["password"]

    topic = "test"
    payload = "Hello, World!"

    client = mqtt.Client()
    client.on_connect = self.on_connect
    client.on_message = self.on_message
    client.username_pw_set(username=f"{username}", password=f"{password}")
    client.connect(f"{host}", 1883, 10)

    client.loop_start()

    publish.single(
      topic=topic,
      payload=payload,
      hostname=f"{host}",
      auth={ "username": f"{username}", "password": f"{password}" }
    )

    time.sleep(10)
    client.loop_stop()

    self.assertEqual(self.code, 0)
    self.assertEqual(self.payload, payload)
