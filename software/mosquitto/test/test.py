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

  message = str()

  def on_connect(client, userdata, flags, rc):
    client.subscribe("test")

  def on_message(client, userdata, msg):
    global topic

    topic = str(msg.topic)
    self.message = str(msg.payload)

  def test_publish_subscribe_ipv4(self):
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

    self.assertEqual(message, payload)
