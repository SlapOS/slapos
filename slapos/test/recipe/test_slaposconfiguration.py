# coding: utf-8
import json
import mock
import os
import shutil
import unittest
import tempfile
from collections import defaultdict
from slapos.recipe import slapconfiguration
from slapos import format as slapformat


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
    self.software_root = tempfile.mkdtemp()

  def tearDown(self):
    os.unlink(self.resource_file)
    os.rmdir(self.instance_root)
    shutil.rmtree(self.software_root)

  @mock.patch("slapos.slap.slap")
  def test_correct_naming(self, _):
    """Test correct naming of variables from resource file."""
    options = defaultdict(str)
    recipe = slapconfiguration.Recipe(self.buildout, "slapconfiguration", options)

    self.assertEqual(options['tun-ipv4'], "192.168.0.1",
      "Folded attrs should be separated by -")
    self.assertIsInstance(options['tun-ipv4'], str)

    self.assertEqual(options['address-list'], [10, 20],
      "All underscores should be replaced with -")

  def writeJsonSchema(self, serialisation='json-in-xml'):
    self.software_json_file = os.path.join(self.software_root, 'software.cfg.json')
    software_schema = {
      "name": "Test",
      "serialisation": serialisation,
      "software-type": {
        "default": {
          "title": "Default",
          "software-type": "default",
          "request": "instance-default-input.json",
          "index": 0,
        },
      }
    }
    with open(self.software_json_file, 'w') as f:
      json.dump(software_schema, f)
    self.instance_json_file = os.path.join(self.software_root, 'instance-default-input.json')
    properties = {
      "letter": {
        "type": "string",
        "enum": ["a", "b", "c"],
        "default": "a"
      },
      "number": {
        "type": "integer",
      },
    }
    default_dict = {}
    without_default = []
    for key, obj in properties.items():
      default = obj.get('default')
      if default is None:
        without_default.append(key)
      else:
        default_dict[key] = default
    self.default_dict = default_dict
    instance_schema = {
      "$schema": "https://json-schema.org/draft/2019-09/schema",
      "$defs": {
        "instance-parameters": {
          "type": "object",
          "properties": properties,
          "required": without_default,
        },
      },
      "unevaluatedProperties": False,
      "allOf": [{"$ref": "#/$defs/instance-parameters" },]
    }
    with open(self.instance_json_file, 'w') as f:
      json.dump(instance_schema, f)

  def patchSlap(self, parameters, serialise, software_type='default'):
    d = {'_': json.dumps(parameters)} if serialise else dict(parameters)
    slap = mock.MagicMock()
    slap_object = slap.return_value
    slap_object.initializeConnection.return_value = None
    computer_partition = slap_object.registerComputerPartition.return_value
    computer_partition.getInstanceParameterDict.return_value = d
    d['ip_list'] = []
    d['slap_software_type'] = software_type
    return mock.patch("slapos.slap.slap", slap)

  def receiveParameters(self):
    options = defaultdict(str)
    options['jsonschema'] = self.software_json_file
    recipe = slapconfiguration.JsonSchema(self.buildout, "slapconfiguration", options)
    return options['configuration']

  def checkParameters(self, received_parameters, sent_parameters):
    expected_dict = dict(self.default_dict)
    expected_dict.update(sent_parameters)
    self.assertEqual(received_parameters, expected_dict)

  def test_jsonschema_json_in_xml_valid_xml_input_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters, False):
      received = self.receiveParameters()
      self.checkParameters(received, parameters)

  def test_jsonschema_json_in_xml_valid_json_input_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters, True):
      received = self.receiveParameters()
      self.checkParameters(received, parameters)

  def test_jsonschema_json_in_xml_valid_xml_input_full(self):
    self.writeJsonSchema()
    parameters = {"letter": "b", "number": 1}
    with self.patchSlap(parameters, False):
      received = self.receiveParameters()
      self.checkParameters(received, parameters)

  def test_jsonschema_json_in_xml_valid_json_input_full(self):
    self.writeJsonSchema()
    parameters = {"letter": "b", "number": 1}
    with self.patchSlap(parameters, True):
      received = self.receiveParameters()
      self.checkParameters(received, parameters)

  def test_jsonschema_json_in_xml_wrong_type_xml_input(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters, False):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )

  def test_jsonschema_json_in_xml_wrong_type_json_input(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters, True):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )

  def test_jsonschema_json_in_xml_incomplete_xml_input(self):
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters, False):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )

  def test_jsonschema_json_in_xml_incomplete_json_input(self):
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters, True):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )
