# coding: utf-8
import mock
import json
import httmock
import os
import unittest
import tempfile
from collections import defaultdict
from slapos.recipe import slapconfiguration
from slapos import format as slapformat


class APIRequestHandler(object):
  def __init__(self, response_list):
    self.response_list = response_list
    self.request_payload_list = []

  def request_handler(self, url, req):
    if url.path == "/getHateoasUrl":
      return ""
    elif url.path == "/getJIOAPIUrl":
      return "https://127.0.0.1/api/"

    if not self.response_list and self.response_list[0][0] != url.path:
      raise ValueError("Unexcpected call: %s %s" % (url.path, req.body))

    return self.response_list.pop(0)[1]


class SlapConfigurationTest(unittest.TestCase):

  def setUp(self):
    """Prepare files on filesystem."""
    self.instance_root = tempfile.mkdtemp()
    # create testing resource file
    self.resource_file = os.path.join(self.instance_root, slapformat.Partition.resource_file)
    self.resource = {
      "tun": {
        "ipv4": u"192.168.0.1"
      },
      "address_list": [
        10, 20
      ]
    }
    with open(self.resource_file, "wt") as fo:
      json.dump(self.resource, fo)
    # do your tests inside try block and clean up in finally
    self.buildout = {
      "buildout": {
        "directory": self.instance_root
      }
    }

  def tearDown(self):
    os.unlink(self.resource_file)
    os.rmdir(self.instance_root)

  @mock.patch("slapos.slap.slap")
  def test_correct_naming(self, MockClient):
    """Test correct naming of variables from resource file."""
    MockClient.initializeConnection.return_value = None
    MockClient.getInstanceParameterDict.return_value = dict()
  
    options = defaultdict(str)
    recipe = slapconfiguration.Recipe(self.buildout, "slapconfiguration", options)

    self.assertEqual(options['tun-ipv4'], "192.168.0.1",
      "Folded attrs should be separated by -")
    self.assertIsInstance(options['tun-ipv4'], str)

    self.assertEqual(options['address-list'], [10, 20],
      "All underscores should be replaced with -")

  def test_new_api(self):
    """Test proper call with new api"""

    options = {
      "url": "http://127.0.0.1:80",
      "software-instance-reference": "SOFTINST-12",
    }
    parameter_dict = {"foo": "bar", "hello": "bye"}
    instance_data = {
      "reference": options["software-instance-reference"],
      "state": "started",
      "software_type": "Couscous",
      "compute_partition_id": "slappartx12",
      "compute_node_id": "COMP-321",
      "software_release_uri": "foo.cfg",
      "processing_timestamp": 1223231231,
      "title": "MyInstance",
      "root_instance_title": "MyInstanceRoot",
      "ip_list": [
        [
          "slaptap9",
          "fe80::1ff:fe23:4567:890a"
        ],
        [
          "slaptap9",
          "10.0.246.114"
        ]
      ],
      "parameters": json.dumps(parameter_dict),
      "connection_parameters": {"1": 2, "3": "YourURL"},
    }
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(instance_data)),
      ("/api/allDocs", json.dumps({"result_list": []}))
    ])
    with httmock.HTTMock(api_handler.request_handler):
      slapconfiguration.Recipe(self.buildout, "slapconfiguration", options)

    self.assertEqual(options["instance-state"], instance_data.get("state"))
    self.assertEqual(options["slap_software_type"], instance_data.get("software_type"))
    self.assertEqual(options["slap_computer_partition_id"], instance_data.get("compute_partition_id"))
    self.assertEqual(options["slap_computer_id"], instance_data.get("compute_node_id"))
    self.assertEqual(options["slap_software_release_url"], instance_data.get("software_release_uri"))
    self.assertEqual(options["timestamp"], instance_data.get("processing_timestamp"))
    self.assertEqual(options["instance-title"], instance_data.get("title"))
    self.assertEqual(options["root-instance-title"], instance_data.get("root_instance_title"))
    self.assertEqual(options["instance-guid"], instance_data.get("reference"))
    self.assertEqual(options["ipv4"], set([instance_data.get("ip_list")[1][1]]))
    self.assertEqual(options["ipv6"], set([instance_data.get("ip_list")[0][1]]))
    for key, value in parameter_dict.items():
      options['configuration.' + key] = value
