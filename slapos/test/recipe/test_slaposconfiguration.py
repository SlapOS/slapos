# coding: utf-8
from zc.buildout import buildout
import copy
import json
import mock
import os
import pickle
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

  def isBuildoutSerializable(self, obj):
    try:
      buildout.dumps(obj)
    except Exception as e:
      self.fail("Object is not serializable by buildout: {e} \n Object: {obj}".format(**{
        "e": e,
        "obj": str(obj)
      }))

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

  SCHEMA = "https://json-schema.org/draft/2020-12/schema"
  FILENAME = '%s-input.json'

  VALID_DEFAULTS = {
    "string": "hello",
    "integer": 42,
    "object": {},
  }

  INVALID_DEFAULTS = {
    "string": 3110,
    "integer": "forty-two",
    "object": None,
  }

  def writeJson(self, filename, content):
    filepath = os.path.join(self.software_root, filename)
    with open(filepath, 'w') as f:
      json.dump(content, f, indent=2)
    return filepath

  def writeSoftwareJson(self, main, shared):
    schemas = []
    schemas.extend((t, False, f) for t, f in main)
    schemas.extend((t, True, f) for t, f in shared)
    self.software_json_file = self.writeJson(
      'software.cfg.json',
      {
        "name": "Test",
        "serialisation": self.serialisation,
        "software-type": {
          t + ('/*' if s else ''): {
            "title": t.capitalize(),
            "software-type": t,
            "shared": s,
            "request": f,
            "index": i,
          }
          for i, (t, s, f) in enumerate(schemas)
        }
      }
    )

  def writeSchema(self, name, schema):
    filename = self.FILENAME % name
    schema.setdefault("$schema", self.SCHEMA)
    self.writeJson(
      filename,
      schema,
    )
    return filename

  def writeObjectSchema(self, name, properties, required=None):
    return self.writeSchema(
      name,
      {
        "$defs": {
          name: {
            "type": "object",
            "properties": properties,
            "required": required or [],
          },
        },
        "unevaluatedProperties": False,
        "allOf": [{"$ref": "#/$defs/" + name},]
      }
    )

  def writeComplexVehiculeSchema(self):
    return self.writeSchema(
      'complex-vehicule',
      {
        "title": "Vehicule",
        "type": "object",
        "oneOf": [
          {
            "title": "Wheeled and motorized (e.g. Car)",
            "type": "object",
            "required": ["wheels", "motor"],
            "properties": {
              "wheels": {},
              "motor": {},
              "windshield-wipers": {
                "type": "boolean",
                "default": True,
              },
            }
          },
          {
            "title": "Wheeled or motorized but not both",
            # The idea is that car-like instances will validate both the
            # bike-like and boat-like subschema, and thus not the oneOf.
            # We need to check that defaults from these locally valid
            # subschemas are not applied to car-like instances!
            # We also need to check that car-like instances do not get
            # any properties unstringified according to these locally
            # valid subschemas!
            "oneOf": [
              {
                "title": "Wheeled but not motorized (e.g. Bike)",
                "type": "object",
                "properties": {
                  "wheels": {},
                  "bell": {
                    "type": "boolean",
                    "default": True,
                  },
                  "lights": {
                    "type": "integer",
                  },
                },
                "required": ["wheels"],
              },
              {
                "title": "Motorized but not wheeled (e.g. Boat)",
                "type": "object",
                "properties": {
                  "motor": {},
                  "propeller": {
                    "type": "boolean",
                    "default": True,
                  },
                },
                "required": ["motor"],
              }
            ]
          },
        ]
      }
    )

  def writeComplexUnevaluatedPropertiesSchema(self):
    # Check that unevaluatedProperties does not result in collecting defaults
    # of sub-schemas that are not actually on a valid validation path.
    return self.writeSchema(
      'complex-unevaluated-properties',
      {
        # The presence of this unevaluatedProperties (whatever its value)
        # triggers a separate validation against each sub-schema of oneOf
        # or anyOf or allOf in any sub-schema of this current schema.
        "unevaluatedProperties": False,
        "type": "object",
        "default": {},
        "oneOf": [
          {
            "properties": {
              "kind": { "const": 1 },
              "a": {},
            },
          },
          {
            "allOf": [
              {
                "properties": {
                  "kind": { "const": 2 },
                },
              },
              {
                # This sub-schema will be validated directly against its
                # sub-instance due to the unevaluatedProperties above.
                "properties": {
                  "a": {
                    # This default should not be collected when kind == 1.
                    "default": "This default should not be collected!",
                  },
                },
              }
            ]
          },
        ]
      }
    )

  def writeComplexAllOfSchema(self):
    return self.writeSchema(
      'complex-allof',
      {
        "type": "object",
        "default": {},
        "oneOf": [
          {
            "allOf": [
              # When kind == 2, this first branch of the allOf fails.
              # This means the allOf as a whole does not validate.
              {
                "properties": {
                  "kind": { "const": 1 },
                },
              },
              # But this branch succeeds. Check that it is not collected.
              # It shouldn't be because the whole allOf does not validate.
              {
                "$ref": self.writeSchema(
                  'complex-allof-ref',
                  {
                    "properties": {
                      "a": {
                        "default": "This default should not be collected!",
                      },
                    },
                  },
                )
              }
            ]
          },
          {
            "properties": {
              "kind": { "const": 2 },
            },
          },
        ]
      }
    )

  def writeComplexJsonSchema(self):
    self.writeSoftwareJson(
      [('default', self.writeComplexVehiculeSchema())],
      []
    )

  def writeJsonSchema(self, valid_defaults=True, ref_thing=True):
    # Main parameters
    main = self.writeObjectSchema(
      'instance-default',
      {
        "letter": {
          "type": "string",
          "enum": ["a", "b", "c"],
          "default": "a" if valid_defaults else 1,
        },
        "number": {
          "type": "integer",
        },
      },
      required=["number"],
    )
    # Shared parameters
    DEFAULTS = self.VALID_DEFAULTS if valid_defaults else self.INVALID_DEFAULTS
    one_of = []
    for i, t in enumerate(("string", "integer"), start=1):
      properties = {
        "kind": {
          "const": i,
        },
        "thing": {
          # This is a property "thing" with a default value defined behind
          # a "$ref". We need to assert this default value is collected!
          "$ref": self.writeSchema(
            'thing-' + t,
            {
              "type": t,
              "default": DEFAULTS[t],
            }
          )
        } if ref_thing else {
          "type": t,
          "default": DEFAULTS[t],
        }
      }
      one_of.append(self.writeObjectSchema(
        'shared-kind-%d' % i,
        properties,
        required=["kind"]
      ))
    shared = 'shared-default-input.json'
    self.writeJson(
      shared,
      {
        "$schema": self.SCHEMA,
        "type": "object",
        "oneOf": [
          {"$ref": ref}  for ref in one_of
        ]
      }
    )
    self.writeSoftwareJson(
      [('default', main)],
      [('default', shared)]
    )

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
    self.mock_computer_partition = computer_partition = slap_object.registerComputerPartition.return_value
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
    self.isBuildoutSerializable(valid)
    self.isBuildoutSerializable(invalid)
    valid = {d['reference']: d['parameters'] for d in valid}
    invalid = {d['reference']: d['parameters'] for d in invalid}
    return valid, invalid

  def recoverStrToInt(self, sent_parameters, keys):
    return {k : int(v) if k in keys else v for k, v in sent_parameters.items()}


class JsonSchemaTest(JsonSchemaTestCase):

  def test_jsonschema_valid_input_with_defaults(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    expected = {"letter": "a", "number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters()
      self.assertEqual(received, expected)

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
    expected = {"letter": "a", "number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'set-default': 'main'})
      self.assertEqual(received, expected)

  def test_jsonschema_valid_input_full(self):
    self.writeJsonSchema()
    parameters = {"letter": "b", "number": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters()
      self.assertEqual(received, parameters)

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

  def test_complex_jsonschema_car_without_defaults(self):
    self.writeComplexJsonSchema()
    # This car-like instance should only obtain defaults from the
    # 'car' schema, not the 'bike' or the 'boat' one, even though
    # it locally validates both, because neither 'bike' nor 'boat'
    # are part of a valid validation path for the whole instance.
    car_parameters = { "wheels": {}, "motor": {}}
    with self.patchSlap(car_parameters):
      received = self.receiveParameters()
      expected = dict(car_parameters, **{'windshield-wipers': True})
      self.assertEqual(received, expected)

  def test_complex_jsonschema_car_unstringify(self):
    self.writeComplexJsonSchema()
    # "4" should not be unstringified, because the 'car' schema
    # does not specify 'lights' is an 'integer', only the 'bike'
    # schema does, and the 'bike' schema is not part of a valid
    # validation path for the whole instance.
    car_parameters = {"wheels": {}, "motor": {}, "lights": "4"}
    with self.patchSlap(car_parameters):
      received = self.receiveParameters({'unstringify': 'main'})
      self.assertEqual(received, car_parameters)

  def test_complex_unevaluated_properties_jsonschema(self):
    self.writeSoftwareJson(
      [('default', self.writeComplexUnevaluatedPropertiesSchema())],
      []
    )
    # Check that unevaluatedProperties does not collect defaults
    # of sub-schemas that are not actually on a valid validation
    # path.
    parameters = {"kind": 1}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'set-default': 'main'})
      self.assertEqual(received, parameters)

  def test_complex_all_of_jsonschema(self):
    # Check that allOf branches are properly discarded, even those
    # that validate the instance and that occur after the branches
    # that do not.
    self.writeSoftwareJson(
      [('default', self.writeComplexAllOfSchema())],
      []
    )
    parameters = {"kind": 2}
    with self.patchSlap(parameters):
      received = self.receiveParameters({'set-default': 'main'})
      self.assertEqual(received, parameters)


class JsonSchemaTestUnserialised(JsonSchemaTest):
  serialise = False


class JsonSchemaTestUnserialisedXml(JsonSchemaTest):
  serialisation = 'xml'
  serialise = False


class JsonSchemaSharedTest(JsonSchemaTestCase):

  def test_jsonschema_shared_1_valid_direct_defaults(self):
    self.writeJsonSchema(ref_thing=False)
    parameters = {"number": 1}
    shared = [{"kind": 1}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (list(valid.values()), invalid),
        ([{"kind": 1, "thing": "hello"}], {})
      )

  def test_jsonschema_shared_2_valid_direct_defaults(self):
    self.writeJsonSchema(ref_thing=False)
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(invalid, {})
      self.assertEqual(list(valid.values()), [{"kind": 2, "thing": 42}])

  def test_jsonschema_shared_1_valid_ref_defaults(self):
    self.writeJsonSchema(ref_thing=True)
    parameters = {"number": 1}
    shared = [{"kind": 1}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(invalid, {})
      self.assertEqual(list(valid.values()), [{"kind": 1, "thing": "hello"}])

  def test_jsonschema_shared_2_valid_ref_defaults(self):
    self.writeJsonSchema(ref_thing=True)
    parameters = {"number": 1}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (list(valid.values()), invalid),
        ([{"kind": 2, "thing": 42}], {})
      )

  def test_jsonschema_shared_1_invalid_defaults(self):
    self.writeJsonSchema(valid_defaults=False)
    parameters = {"number": 1, "letter": "a"}
    shared = [{"kind": 1}]
    with self.patchSlap(parameters, shared):
      # Invalid defaults are not applied but make the instance appear invalid
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (valid, list(invalid.values())),
        ({}, [{"kind": 1}])
      )

  def test_jsonschema_shared_2_invalid_defaults(self):
    self.writeJsonSchema(valid_defaults=False)
    parameters = {"number": 1, "letter": "a"}
    shared = [{"kind": 2}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      # Invalid defaults are not applied but make the instance appear invalid
      self.assertEqual(
        (valid, list(invalid.values())),
        ({}, [{"kind": 2}])
      )

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
      expected = [{"kind": 1, "thing": "hello"}, {"kind": 2, "thing": 42}]
      self.assertEqual(
        (list(valid.values()), invalid),
        (expected, {})
      )

  def test_jsonschema_shared_invalid_kind(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (valid, list(invalid.values())),
        ({}, [{"kind": 0}])
      )

  def test_jsonschema_shared_1_invalid_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1, "thing": {}}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (valid, list(invalid.values())),
        ({}, [{"kind": 1, "thing": {}}])
      )

  def test_jsonschema_shared_2_invalid_thing(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 2, "thing": {}}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (valid, list(invalid.values())),
        ({}, [{"kind": 2, "thing": {}}])
      )

  def test_jsonschema_shared_2_unstringify_direct_thing(self):
    self.writeJsonSchema(ref_thing=False)
    parameters = {"number": 1}
    shared = [{"kind": 2, "thing": "1"}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters({'unstringify': 'shared'})
      recovered = self.recoverStrToInt(shared[0], ('thing',))
      self.assertEqual(
        (list(valid.values()), invalid),
        ([recovered], {})
      )

  def test_jsonschema_shared_2_unstringify_ref_thing(self):
    self.writeJsonSchema(ref_thing=True)
    parameters = {"number": 1}
    shared = [{"kind": 2, "thing": "1"}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters({'unstringify': 'shared'})
      recovered = self.recoverStrToInt(shared[0], ('thing',))
      self.assertEqual(
        (list(valid.values()), invalid),
        ([recovered], {})
      )

  def test_jsonschema_shared_valid_and_invalid(self):
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 1}, {"kind": 2, "thing": "hello"}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(
        (list(valid.values()), list(invalid.values())),
        ([{"kind": 1, "thing": "hello"}], [{"kind": 2, "thing": "hello"}])
      )

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


class JsonSchemaReportErrorTest(JsonSchemaTestCase):

  MAIN_MISSING_NUMBER_ERROR = (
    "Invalid parameters:\n"
    "  $: 'number' is a required property"
  )

  def test_report_error_main_default(self):
    """Main validation error is reported to master by default (report-error='all')."""
    self.writeJsonSchema()
    parameters = {}  # missing required "number"
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
      )
      self.mock_computer_partition.error.assert_called_once()
      args, kwargs = self.mock_computer_partition.error.call_args
      self.assertEqual(args[0], self.MAIN_MISSING_NUMBER_ERROR)

  def test_report_error_main_only(self):
    """Main validation error is reported when report-error='main'."""
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'report-error': 'main'},
      )
      self.mock_computer_partition.error.assert_called_once()
      args, kwargs = self.mock_computer_partition.error.call_args
      self.assertEqual(args[0], self.MAIN_MISSING_NUMBER_ERROR)

  def test_report_error_main_none(self):
    """Main validation error is NOT reported when report-error='none'."""
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'report-error': 'none'},
      )
      self.mock_computer_partition.error.assert_not_called()

  def test_report_error_main_shared_only(self):
    """Main validation error is NOT reported when report-error='shared'."""
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters):
      self.assertRaises(
        slapconfiguration.UserError,
        self.receiveParameters,
        {'report-error': 'shared'},
      )
      self.mock_computer_partition.error.assert_not_called()

  def test_report_error_main_still_raises(self):
    """Main validation still raises UserError even after reporting."""
    self.writeJsonSchema()
    parameters = {}
    with self.patchSlap(parameters):
      with self.assertRaises(slapconfiguration.UserError):
        self.receiveParameters({'report-error': 'all'})
      self.mock_computer_partition.error.assert_called_once()
      args, kwargs = self.mock_computer_partition.error.call_args
      self.assertEqual(args[0], self.MAIN_MISSING_NUMBER_ERROR)

  SHARED_INVALID_KIND_ERROR = (
    "  $: {'kind': 0} is not valid under any of the given schemas"
  )

  def test_report_error_shared_default(self):
    """Shared validation errors are reported to master by default with slave_reference."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}]  # invalid kind
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(len(invalid), 1)
      self.mock_computer_partition.error.assert_called_once()
      args, kwargs = self.mock_computer_partition.error.call_args
      self.assertEqual(kwargs['slave_reference'], 'SHARED0')
      self.assertEqual(args[0], self.SHARED_INVALID_KIND_ERROR)

  def test_report_error_shared_only(self):
    """Shared validation errors are reported when report-error='shared'."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters(
        {'set-default': 'all', 'report-error': 'shared'})
      self.assertEqual(len(invalid), 1)
      self.mock_computer_partition.error.assert_called_once()
      args, kwargs = self.mock_computer_partition.error.call_args
      self.assertEqual(args[0], self.SHARED_INVALID_KIND_ERROR)

  def test_report_error_shared_none(self):
    """Shared validation errors are NOT reported when report-error='none'."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters(
        {'set-default': 'all', 'report-error': 'none'})
      self.assertEqual(len(invalid), 1)
      self.mock_computer_partition.error.assert_not_called()

  def test_report_error_shared_main_only(self):
    """Shared validation errors are NOT reported when report-error='main'."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters(
        {'set-default': 'all', 'report-error': 'main'})
      self.assertEqual(len(invalid), 1)
      self.mock_computer_partition.error.assert_not_called()

  # Both kind and thing become unevaluated in each oneOf branch because the
  # failing sub-schema discards its properties annotation.  When multiple
  # properties are unevaluated, jsonschema groups them into a single error.
  # Branch 1 (kind=1): kind fails const=1 → both unevaluated + const error.
  # Branch 2 (kind=2): thing fails type=integer → both unevaluated + type error.
  SHARED_INVALID_THING_ERROR = (
    "  $: {'kind': 2, 'thing': 'hello'} is not valid under any of the given schemas"
  )

  def test_report_error_shared_multiple_invalid(self):
    """Each invalid shared instance is reported separately with its slave_reference."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}, {"kind": 2, "thing": "hello"}]
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(len(invalid), 2)
      self.assertEqual(self.mock_computer_partition.error.call_count, 2)
      calls = self.mock_computer_partition.error.call_args_list
      self.assertEqual(calls[0][1]['slave_reference'], 'SHARED0')
      self.assertEqual(calls[1][1]['slave_reference'], 'SHARED1')
      self.assertEqual(calls[0][0][0], self.SHARED_INVALID_KIND_ERROR)
      self.assertEqual(calls[1][0][0], self.SHARED_INVALID_THING_ERROR)

  def test_report_error_main_no_json_path_notation(self):
    """Error messages use readable parameter names, not JSON path $ notation."""
    self.writeJsonSchema()
    parameters = {"number": "not_a_number"}
    with self.patchSlap(parameters):
      with self.assertRaises(slapconfiguration.UserError) as cm:
        self.receiveParameters()
      error_msg = str(cm.exception)
      # unevaluatedProperties fires because the allOf sub-schema fails
      # (annotations from failing schemas are discarded per JSON Schema spec),
      # followed by the type error on the path to the property.
      self.assertEqual(
        error_msg,
        "Invalid parameters:\n"
        "  $: Unevaluated properties are not allowed ('number' was unexpected)\n"
        "  $.number: 'not_a_number' is not of type 'integer'",
      )

  def test_report_error_shared_expands_context(self):
    """Shared oneOf validation errors expand context sub-errors."""
    self.writeJsonSchema()
    parameters = {"number": 1}
    shared = [{"kind": 0}]  # invalid: neither kind 1 nor kind 2
    with self.patchSlap(parameters, shared):
      valid, invalid = self.receiveSharedParameters()
      self.assertEqual(len(invalid), 1)
      self.mock_computer_partition.error.assert_called_once()
      args, kwargs = self.mock_computer_partition.error.call_args
      self.assertEqual(args[0], self.SHARED_INVALID_KIND_ERROR)
