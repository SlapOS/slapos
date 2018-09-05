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

import unittest
import os
import glob
import json
import collections
import slapos.test
import jsonschema


def getSchemaValidator(filename):
  schema_json_file = "/".join(slapos.test.__file__.split("/")[:-1])
  schema_json_file += "/%s" % filename
  with open(schema_json_file, "r") as json_file:
    json_dict = json.loads(json_file.read())
    json_file.close()
  return json_dict

def createValidatorTest(path, json_dict):
  # Test that json is valid
  def run(self, *args, **kwargs):
    with open(path, "r") as json_file:
      self.assertEqual(jsonschema.validate(json.load(json_file), json_dict), None)

  return run

def createFormatTest(path, json_dict):
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
  json_dict = getSchemaValidator("schema.json")
  base_path = "/".join(slapos.test.__file__.split("/")[:-3])
  for path in glob.glob("%s/software/*/software.cfg.json" % base_path):
    test_name = "test_%s_software_cfg_json" % path.split("/")[-2]
    setattr(TestJSONSchemaValidation, test_name, createValidatorTest(path, json_dict))
    setattr(TestJSONSchemaValidation, test_name + '_format', createFormatTest(path, json_dict))


def generateJSONSchemaTest():
  json_dict = getSchemaValidator("metaschema.json")
  base_path = "/".join(slapos.test.__file__.split("/")[:-3])
  for path in glob.glob("%s/software/*/*schema.json" % base_path):
    software_type = path.split("/")[-2]
    filename = path.split("/")[-1].replace("-", "_").replace(".", "_")
    test_name = "test_schema_%s_%s" % (software_type, filename)
    setattr(TestJSONSchemaValidation, test_name, createValidatorTest(path, json_dict))
    setattr(TestJSONSchemaValidation, test_name + '_format', createFormatTest(path, json_dict))

class TestJSONSchemaValidation(unittest.TestCase):
  pass

generateSoftwareCfgTest()
generateJSONSchemaTest()

if __name__ == '__main__':
  unittest.main()
