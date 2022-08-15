##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import collections
import glob
import json
import os
import unittest

import jsonschema
import six

import slapos.test

def createInstanceParameterSchemaValidatorTest(path):
  # Test that json is a valid json schema, supports several
  # validator, depending on the `$schema` defined in the json.
  validator_dict = {
    "http://json-schema.org/draft-03/schema#": jsonschema.Draft3Validator,
    "http://json-schema.org/draft-04/schema": jsonschema.Draft4Validator,
    "http://json-schema.org/draft-04/schema#": jsonschema.Draft4Validator,
    "http://json-schema.org/draft-06/schema#": jsonschema.Draft6Validator,
    "http://json-schema.org/draft-07/schema#": jsonschema.Draft7Validator,
  }
  def run(self, *args, **kwargs):
    with open(path, "r") as json_file:
      json_dict = json.load(json_file)
      validator = validator_dict.get(
        json_dict.get('$schema'),
        jsonschema.Draft7Validator)
      validator.check_schema(json_dict)
  return run


def createSoftwareCfgValidatorTest(path, software_cfg_schema):
  # Test that software json follows the schema for softwares json,
  # which is defined in schema.json in this directory
  def run(self, *args, **kwargs):
    with open(path, "r") as json_file:
      schema = json.load(json_file)
      jsonschema.validate(schema, software_cfg_schema)

      # also make sure request and response schemas can be resolved
      schema.setdefault('$id', 'file://' + path)
      resolver = jsonschema.RefResolver.from_schema(schema)
      for software_type_definition in six.itervalues(schema['software-type']):
        resolver.resolve(software_type_definition['request'])
        resolver.resolve(software_type_definition['response'])

  return run


def createFormatTest(path):
  # Test that json match our formatting rules
  def run(self, *args, **kwargs):
    with open(path, "r") as json_file:
      content = json_file.read()
      # this is the format produced by `format-json` tool at the
      # root of this repository.
      # XXX it would be better to reuse the code.
      self.assertEqual(
          (json.dumps(
              json.loads(content, object_pairs_hook=collections.OrderedDict),
              sort_keys=False,
              indent=2,
              separators=(',', ': ')) + "\n").splitlines(),
          content.splitlines())
  return run


def generateSoftwareCfgTest():
  software_cfg_schema = json.load(
    open(os.path.join(
        os.path.dirname(slapos.test.__file__),
        "schema.json"), 'r'))
  base_path = "/".join(slapos.test.__file__.split("/")[:-3])
  for path in glob.glob("%s/software/*/software.cfg.json" % base_path):
    test_name = "test_%s_software_cfg_json" % path.split("/")[-2]
    setattr(TestJSONSchemaValidation, test_name, createSoftwareCfgValidatorTest(path, software_cfg_schema))
    setattr(TestJSONSchemaValidation, test_name + '_format', createFormatTest(path))


def generateJSONSchemaTest():
  base_path = "/".join(slapos.test.__file__.split("/")[:-3])
  for path in glob.glob("%s/software/*/*schema.json" % base_path):
    software_type = path.split("/")[-2]
    filename = path.split("/")[-1].replace("-", "_").replace(".", "_")
    test_name = "test_schema_%s_%s" % (software_type, filename)
    setattr(TestJSONSchemaValidation, test_name, createInstanceParameterSchemaValidatorTest(path))
    setattr(TestJSONSchemaValidation, test_name + '_format', createFormatTest(path))


class TestJSONSchemaValidation(unittest.TestCase):
  pass

generateSoftwareCfgTest()
generateJSONSchemaTest()

if __name__ == '__main__':
  unittest.main()
