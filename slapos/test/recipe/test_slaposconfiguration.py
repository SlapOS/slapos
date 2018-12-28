# coding: utf-8
import json
import mock
import os
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
