# coding: utf-8
import json
import httmock
import os
import unittest
import tempfile
from slapos.recipe import publish
from slapos.recipe.librecipe import wrap
from slapos.grid.SlapObject import SOFTWARE_INSTANCE_JSON_FILENAME
from test_slaposconfiguration import APIRequestHandler


class PublishTestMixin(object):

  def setUp(self):
    """Prepare files on filesystem."""
    self.instance_root = tempfile.mkdtemp()
    self.instance_json_location = os.path.join(
      self.instance_root,
      SOFTWARE_INSTANCE_JSON_FILENAME
    )
    # do your tests inside try block and clean up in finally
    self.buildout = {
      "buildout": {
        "directory": self.instance_root
      },
      "slap-connection": {
        "computer-id": "COMP-12",
        "partition-id": "slappart12",
        "server-url": "http://127.0.0.1:80",
        "software-release-url": "foo.cfg",
      },
    }

  def tearDown(self):
    if os.path.exists(self.instance_json_location):
      os.unlink(self.instance_json_location)
    os.rmdir(self.instance_root)

  def test_publish_connection_information(self):
    """Test proper call with new api"""
    options = {
      "foo": "bar",
      "hello": "bye",
    }
    self.buildout["publish"] = options
    if self.serialised:
      connection_parameters = wrap({"foo": "bar"})
    else:
      connection_parameters = {"foo": "bar"}
    instance_data = {
      "reference": "SOFTINST-12",
      "connection_parameters": connection_parameters,
    }
    if self.use_api:
      api_handler = APIRequestHandler([
        ("/api/get/", json.dumps(instance_data)),
        ("/api/put/", "{}")
      ])
    else:
      with open(self.instance_json_location, 'w') as f:
        json.dump(instance_data, f, indent=2)
      api_handler = APIRequestHandler([
        ("/api/put/", "{}")
      ])
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.publish_recipe(self.buildout, "publish", options)
      recipe.install()

    if self.serialised:
      options = wrap(options)

    self.assertEqual(
      api_handler.request_payload_list[-1],
      {
        "reference": instance_data["reference"],
        "portal_type": "Software Instance",
        "connection_parameters": options
      }
    )

  def test_publish_connection_not_needed(self):
    """Test proper call with new api"""
    options = {
      "foo": "bar",
      "hello": "bye",
    }
    self.buildout["publish"] = options
    if self.serialised:
      connection_parameters = wrap(options)
    else:
      connection_parameters = options
    instance_data = {
      "reference": "SOFTINST-12",
      "connection_parameters": connection_parameters,
    }
    if self.use_api:
      api_handler = APIRequestHandler([
        ("/api/get/", json.dumps(instance_data)),
      ])
    else:
      with open(self.instance_json_location, 'w') as f:
        json.dump(instance_data, f, indent=2)
      api_handler = APIRequestHandler([])
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.publish_recipe(self.buildout, "publish", options)
      recipe.install()

class PublishWithLocalInstanceFile(PublishTestMixin, unittest.TestCase):
  use_api = False
  publish_recipe = publish.Recipe
  serialised = False

class PublishWithApi(PublishTestMixin, unittest.TestCase):
  use_api = True
  publish_recipe = publish.Recipe
  serialised = False

class PublishSerialiseWithLocalInstanceFile(PublishTestMixin, unittest.TestCase):
  use_api = False
  publish_recipe = publish.Serialised
  serialised = True

class PublishSerialiseWithApi(PublishTestMixin, unittest.TestCase):
  use_api = True
  publish_recipe = publish.Serialised
  serialised = True
