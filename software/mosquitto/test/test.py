import os
import paho.mqtt.publish as publish
import paho.mqtt.subscribe as subscribe
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

class MosquittoTestCase(SlapOSInstanceTestCase):

  name = None
  kind = None

  @classmethod
  def getInstanceParameterDict(cls):
    return { "name": cls.name }


class MQTTRequestTestMixin:

  """
  Test if mosquitto service can publish and subscribe
  to specific topics with custom authentications ...
  """

  def test_publish_subscribe_ipv4(self):
    host = self.computer_partition.getConnectionParameterDict()["ipv4-ip"]
    username = self.computer_partition.getConnectionParameterDict()["username"]
    password = self.computer_partition.getConnectionParameterDict()["password"]

    message = subscribe.simple(
      topics="test",
      hostname=f"{host}",
      auth={ "username": f"{username}", "password": f"{password}" }
    )

    publish.single(
      topic="test",
      payload="Hello, World! I'm just testing ...",
      hostname=f"{host}",
      auth={ "username": f"{username}", "password": f"{password}" }
    )

    self.assertEqual(f"{message.topic}: {message.payload}", "test: b\"Hello, World! I'm just testing ...\"")
