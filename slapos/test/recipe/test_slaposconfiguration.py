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


class SlapConfigurationTestCase(unittest.TestCase):

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


class SlapConfigurationTest(SlapConfigurationTestCase):

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


class JsonSchemaTestCase(SlapConfigurationTestCase):
  serialisation='json-in-xml'
  serialise = True

  def writeJsonSchema(self, valid_defaults=True):
    self.software_json_file = os.path.join(self.software_root, 'software.cfg.json')
    software_schema = {
      "name": "Test",
      "serialisation": self.serialisation,
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
        "default": "a" if valid_defaults else 1,
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
          "default": "hello" if valid_defaults else 1,
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
          "default": 42 if valid_defaults else "forty-two",
        },
      },
      "required": ["kind"],
    }
    with open(self.shared_2_json_file, 'w') as f:
      json.dump(shared_2_schema, f)


  def patchSlap(self, parameters, shared=None, software_type='default'):
    shared = copy.deepcopy(shared) if shared else []
    if self.serialise:
      d = {'_': json.dumps(parameters, sort_keys=True)}
      shared = [{'_': json.dumps(s, sort_keys=True)} for s in shared]
    else:
      d = copy.deepcopy(parameters)
    for i, s in enumerate(shared):
      s['slave_reference'] = 'SHARED%s' % i
    slap = mock.MagicMock()
    slap_object = slap.return_value
    slap_object.initializeConnection.return_value = None
    computer_partition = slap_object.registerComputerPartition.return_value
    computer_partition.getInstanceParameterDict.return_value = d
    d['ip_list'] = []
    d['slap_software_type'] = software_type
    d['slave_instance_list'] = shared
    return mock.patch("slapos.slap.slap", slap)

  def runJsonSchemaRecipe(self, options=()):
    options = defaultdict(str, options)
    options['jsonschema'] = self.software_json_file
    slapconfiguration.JsonSchema(self.buildout, "slapconfiguration", options)
    return options

  def receiveParameters(self, options=(('set-default', 'all'),)):
    options = self.runJsonSchemaRecipe(options)
    return options['configuration']

  def receiveSharedParameters(self, options=(('set-default', 'all'),)):
    options = self.runJsonSchemaRecipe(options)
    self.assertNotIn('slave-instance-list', options)
    valid = options['valid-shared-instance-list']
    invalid = options['invalid-shared-instance-list']
    valid = {d['reference']: d['parameters'] for d in valid}
    invalid = {d['reference']: d['parameters'] for d in invalid}
    return valid, invalid

  def checkParametersWithDefaults(self, received_parameters, sent_parameters):
    expected_dict = dict(self.default_dict)
    expected_dict.update(sent_parameters)
    self.assertEqual(received_parameters, expected_dict)

  def recoverStrToInt(self, sent_parameters, keys):
    return {k : int(v) if k in keys else v for k, v in sent_parameters.items()}


class JsonSchemaTest(JsonSchemaTestCase):

  def test_jsonschema_valid_input_with_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters()
      self.checkParametersWithDefaults(received, parameters)

  def test_jsonschema_valid_input_without_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters(options=())
      self.assertEqual(received, parameters)

  def test_jsonschema_valid_input_with_only_shared_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'set-default': 'shared'})
      self.assertEqual(received, parameters)

  def test_jsonschema_valid_input_with_only_main_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'set-default': 'main'})
      self.checkParametersWithDefaults(received, parameters)

  def test_jsonschema_valid_input_full(self):
    self.writeJsonSchema()
    parameters = {"letter": "b", "number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters()
      self.checkParametersWithDefaults(received, parameters)

  def test_jsonschema_wrong_type_input(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )

  def test_jsonschema_unstringify_input(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'unstringify': 'main'})
      recovered = self.recoverStrToInt(parameters, ('number',))
      self.assertEqual(received, recovered)

  def test_jsonschema_incomplete_input(self):
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )

  def test_jsonschema_invalid_defaults_input(self):
    self.writeJsonSchema(valid_defaults=False)
    parameters = {"number": 1}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )


class JsonSchemaTestUnserialised(JsonSchemaTest):
  serialise = False


class JsonSchemaTestUnserialisedXml(JsonSchemaTest):
  serialisation = 'xml'
  serialise = False


class JsonSchemaSharedTest(JsonSchemaTestCase):

  def test_jsonschema_shared_1_valid_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(invalid, {})
      self.assertEqual(list(valid.values()), [{"kind": 1, "thing": "hello"}])

  def test_jsonschema_shared_2_valid_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(invalid, {})
      self.assertEqual(list(valid.values()), [{"kind": 2, "thing": 42}])

  def test_jsonschema_shared_1_invalid_defaults(self):
    self.writeJsonSchema(valid_defaults=False)
    parameters = {"number": 1, "letter": "a"}
    shared = [{"kind": 1}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 1, "thing": 1}])

  def test_jsonschema_shared_2_invalid_defaults(self):
    self.writeJsonSchema(valid_defaults=False)
    parameters = {"number": 1, "letter": "a"}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(valid, {})
      invalid_values = list(invalid.values())
      self.assertEqual(invalid_values, [{"kind": 2, "thing": "forty-two"}])

  def test_jsonschema_shared_2_valid_without_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, _ = self.receiveSharedParameters(options=())
      self.assertEqual(list(valid.values()), shared)

  def test_jsonschema_shared_2_valid_with_only_main_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, _ = self.receiveSharedParameters({'set-default': 'main'})
      self.assertEqual(list(valid.values()), shared)

  def test_jsonschema_shared_2_valid_with_only_shared_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, _ = self.receiveSharedParameters({'set-default': 'shared'})
      self.assertEqual(list(valid.values()), [{"kind": 2, "thing": 42}])

  def test_jsonschema_shared_1_and_2_valid_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(invalid, {})
      expected = [{"kind": 1, "thing": "hello"}, {"kind": 2, "thing": 42}]
      self.assertEqual(list(valid.values()), expected)

  def test_jsonschema_shared_invalid_kind(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 3}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 3}])

  def test_jsonschema_shared_1_invalid_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1, "thing": {}}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 1, "thing": {}}])

  def test_jsonschema_shared_2_invalid_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2, "thing": {}}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(valid, {})
      self.assertEqual(list(invalid.values()), [{"kind": 2, "thing": {}}])

  def test_jsonschema_shared_2_unstringify_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2, "thing": "1"}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters({'unstringify': 'shared'})
      recovered = self.recoverStrToInt(shared[0], ('thing',))
      self.assertEqual(list(valid.values()), [recovered])
      self.assertEqual(invalid, {})

  def test_jsonschema_shared_valid_and_invalid(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2, "thing": "hello"}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(list(valid.values()), [{"kind": 1, "thing": "hello"}])
      self.assertEqual(list(invalid.values()), [{"kind": 2, "thing": "hello"}])

  def test_jsonschema_shared_valid_and_invalid_skip_shared(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2, "thing": "hello"}]
    with self.patchSlap(parameters, shared):
      options = self.runJsonSchemaRecipe({'validate-parameters': 'main'})
      received = options['slave-instance-list']
      self.assertEqual(
        received,
        [
          dict(
            slave_reference = "SHARED%d" % i,
            **{'_': json.dumps(d, sort_keys=True)} if self.serialise else d
          )
          for i, d in enumerate(shared)
        ],
      )


class JsonSchemaSharedTestUnserialised(JsonSchemaSharedTest):
  serialise = False


class JsonSchemaSharedTestUnserialisedXml(JsonSchemaSharedTest):
  serialisation = 'xml'
  serialise = False


class JsonSchemaTestMisc(JsonSchemaTestCase):
  def test_jsonschema_wrong_type_input_skip_main(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'validate-parameters': 'shared'})
      self.assertEqual(received, parameters)

  def test_jsonschema_wrong_type_input_skip_shared(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'validate-parameters': 'main'},
      )

  def test_jsonschema_unstringify_skip_main(self):
    self.writeJsonSchema()
    parameters = {"number": "1"}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'unstringify': 'shared'},
      )

  def test_jsonschema_shared_valid_and_invalid_skip_main(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2, "thing": "hello"}]
    with self.patchSlap(parameters, shared):
      options = {'validate-parameters': 'shared', 'set-default': 'all'}
      valid, invalid = self.receiveSharedParameters(options)
      self.assertEqual(list(valid.values()), [{"kind": 1, "thing": "hello"}])
      self.assertEqual(list(invalid.values()), [{"kind": 2, "thing": "hello"}])

  def test_jsonschema_shared_no_slaves(self):
    """Test that [in]valid-shared-instance-list exists as an empty list when there are no slaves."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters, shared=[]):
      options = self.runJsonSchemaRecipe()
      self.assertIn('valid-shared-instance-list', options)
      self.assertEqual(options['valid-shared-instance-list'], [])
      self.assertIn('invalid-shared-instance-list', options)
      self.assertEqual(options['invalid-shared-instance-list'], [])

  def test_jsonschema_non_existing_main_software_type(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters, software_type='nonexistent'):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'validate-parameters': 'main'},
      )

  def test_jsonschema_non_existing_shared_software_type_without_shared(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    with self.patchSlap(parameters, software_type='nonexistent'):
      received = self.receiveParameters({'validate-parameters': 'shared'})
      self.assertEqual(received, parameters)

  def test_jsonschema_non_existing_shared_software_type_with_shared(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2}]
    with self.patchSlap(parameters, shared=shared, software_type='nonexistent'):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'validate-parameters': 'shared'},
      )
