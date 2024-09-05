# coding: utf-8
import copy
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
        "default/*": {
          "title": "Default",
          "shared": True,
          "software-type": "default",
          "request": "shared-default-input.json",
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
    self.shared_json_file = os.path.join(self.software_root, 'shared-default-input.json')
    shared_schema = {
      "$schema": "https://json-schema.org/draft/2019-09/schema",
      "type": "object",
      "oneOf": [
        {
          "$ref": "shared-1-default-input.json"
        },
        {
          "$ref": "shared-2-default-input.json"
        },
      ]
    }
    with open(self.shared_json_file, 'w') as f:
      json.dump(shared_schema, f)
    self.shared_1_json_file = os.path.join(self.software_root, 'shared-1-default-input.json')
    shared_1_schema = {
      "$schema": "https://json-schema.org/draft/2019-09/schema",
      "type": "object",
      "properties": {
        "kind": {
          "const": 1,
        },
        "thing": {
          "type": "string",
          "default": "hello",
        },
      },
      "required": ["kind"],
    }
    with open(self.shared_1_json_file, 'w') as f:
      json.dump(shared_1_schema, f)
    self.shared_2_json_file = os.path.join(self.software_root, 'shared-2-default-input.json')
    shared_2_schema = {
      "$schema": "https://json-schema.org/draft/2019-09/schema",
      "type": "object",
      "properties": {
        "kind": {
          "const": 2,
        },
        "thing": {
          "type": "integer",
          "default": 42,
        },
        "required": ["kind"],
      }
    }
    with open(self.shared_2_json_file, 'w') as f:
      json.dump(shared_2_schema, f)


  def patchSlap(self, parameters, serialise, shared=(), software_type='default'):
    parameters = copy.deepcopy(parameters)
    shared = copy.deepcopy(shared)
    d = {'_': json.dumps(parameters)} if serialise else dict(parameters)
    for i, s in enumerate(shared):
      s['slave_reference'] = 'SHARED%s' % i
    slap = mock.MagicMock()
    slap_object = slap.return_value
    slap_object.initializeConnection.return_value = None
    computer_partition = slap_object.registerComputerPartition.return_value
    computer_partition.getInstanceParameterDict.return_value = d
    d['ip_list'] = []
    d['slap_software_type'] = software_type
    d['slave_instance_list'] = list(shared)
    return mock.patch("slapos.slap.slap", slap)

  def receiveParameters(self, shared=False):
    options = defaultdict(str)
    options['jsonschema'] = self.software_json_file
    recipe = slapconfiguration.JsonSchema(self.buildout, "slapconfiguration", options)
    if shared:
      valid = options['slave-instance-list']
      invalid = options['invalid-slave-instance-list']
      valid = {d['reference']: d['parameters'] for d in valid}
      invalid = {d['reference']: d['parameters'] for d in invalid}
      return valid, invalid
    else:
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

  def test_jsonschema_shared_1_valid_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(invalid, {})
      self.assertEqual(list(valid.values()), [{"kind": 1, "thing": "hello"}])

  def test_jsonschema_shared_2_valid_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(invalid, {})
      self.assertEqual(list(valid.values()), [{"kind": 2, "thing": 42}])

  def test_jsonschema_shared_1_and_2_valid_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(invalid, {})
      expected = [{"kind": 1, "thing": "hello"}, {"kind": 2, "thing": 42}]
      self.assertEqual(list(valid.values()), expected)

  def test_jsonschema_shared_invalid_kind(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 3}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 3}])

  def test_jsonschema_shared_1_invalid_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1, "thing": {}}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 1, "thing": {}}])

  def test_jsonschema_shared_2_invalid_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2, "thing": {}}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 2, "thing": {}}])

  def test_jsonschema_shared_valid_and_invalid(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2, "thing": "hello"}]
    with self.patchSlap(parameters, True, shared):
      valid, invalid = self.receiveParameters(shared=True)
      self.assertEqual(list(valid.values()), [{"kind": 1, "thing": "hello"}])
      self.assertEqual(list(invalid.values()), [{"kind": 2, "thing": "hello"}])
