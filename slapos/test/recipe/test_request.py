import httmock
import json
import mock
import os
import unittest
import tempfile
from collections import defaultdict
from slapos.recipe import request
from slapos.slap.slap import COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME
from test_slaposconfiguration import APIRequestHandler
from testfixtures import LogCapture


class RecipeTestMixin(object):

  def setUp(self):
    self.buildout = {
      "buildout": {
      },
      "slap-connection": {
      }
    }
    slap_patch = mock.patch(
      "slapos.recipe.request.slapmodule.slap", autospec=True)
    slap = slap_patch.start()
    self.addCleanup(slap_patch.stop)
    slap_instance = mock.MagicMock()
    self.request_instance = mock.MagicMock()
    register_instance = mock.MagicMock()
    requested_instance = mock.MagicMock()
    self.request_instance.return_value = requested_instance
    register_instance.request = self.request_instance
    slap_instance.registerComputerPartition.return_value = register_instance
    slap_instance.jio_api_connector = None
    slap.return_value = slap_instance
    self.instance_getConnectionParameter = \
        requested_instance.getConnectionParameter

  def test_no_return_in_options_logs(self):
    options = defaultdict(str)
    self.instance_getConnectionParameter.return_value = self.return_value_empty
    with LogCapture() as log:
      self.recipe(self.buildout, "request", options)
    log.check(
      ('request', 'DEBUG',
       'No parameter to return to main instance.Be careful about that...'),
    )
    self.request_instance.assert_called_with(
      '', 'RootSoftwareInstance', '', filter_kw={},
      partition_parameter_kw=self.called_partition_parameter_kw,
      shared=False, state='started')

  def test_return_in_options_logs(self):
    options = defaultdict(str)
    options['return'] = 'anything'

    self.instance_getConnectionParameter.return_value = self.return_value_empty

    with LogCapture() as log:
      self.recipe(self.buildout, "request", options)
    log.check()
    self.request_instance.assert_called_with(
      '', 'RootSoftwareInstance', '', filter_kw={},
      partition_parameter_kw=self.called_partition_parameter_kw,
      shared=False, state='started')

  def test_return_not_ready(self):
    options = defaultdict(str)
    options['return'] = 'anything'

    self.instance_getConnectionParameter.side_effect = \
        request.slapmodule.NotFoundError()

    recipe = self.recipe(self.buildout, "request", options)
    if self.raises:
      self.assertRaises(KeyError, recipe.install)
    self.assertEqual(options['connection-anything'], '')
    self.request_instance.assert_called_with(
      '', 'RootSoftwareInstance', '', filter_kw={},
      partition_parameter_kw=self.called_partition_parameter_kw,
      shared=False, state='started')

  def test_return_ready(self):
    options = defaultdict(str)
    options['return'] = 'anything'

    self.instance_getConnectionParameter.return_value = self.return_value

    recipe = self.recipe(self.buildout, "request", options)
    result = recipe.install()
    self.assertEqual([], result)
    self.assertEqual(options['connection-anything'], 'done')
    self.assertIsInstance(options['connection-anything'], str)
    self.request_instance.assert_called_with(
      '', 'RootSoftwareInstance', '', filter_kw={},
      partition_parameter_kw=self.called_partition_parameter_kw,
      shared=False, state='started')

  def test_requester_stopped_state_propagated(self):
    options = defaultdict(str)
    options['return'] = 'anything'
    self.buildout['slap-connection']['requested'] = 'stopped'

    self.instance_getConnectionParameter.return_value = self.return_value_empty

    with LogCapture() as log:
      self.recipe(self.buildout, "request", options)
    log.check()
    self.request_instance.assert_called_with(
      '', 'RootSoftwareInstance', '', filter_kw={},
      partition_parameter_kw=self.called_partition_parameter_kw,
      shared=False, state='stopped')

  def test_requester_destroyed_state_not_propagated(self):
    options = defaultdict(str)
    options['return'] = 'anything'
    self.buildout['slap-connection']['requested'] = 'destroyed'

    self.instance_getConnectionParameter.return_value = self.return_value_empty

    with LogCapture() as log:
      self.recipe(self.buildout, "request", options)
    log.check()
    self.request_instance.assert_called_with(
      '', 'RootSoftwareInstance', '', filter_kw={},
      partition_parameter_kw=self.called_partition_parameter_kw,
      shared=False, state='started')

class RecipeTest(RecipeTestMixin, unittest.TestCase):
  recipe = request.Recipe
  raises = True
  return_value_empty = {}
  return_value = 'done'
  called_partition_parameter_kw = {}


class RequestOptionalTest(RecipeTestMixin, unittest.TestCase):
  recipe = request.RequestOptional
  raises = False
  return_value = 'done'
  return_value_empty = {}
  called_partition_parameter_kw = {}


class RequestJSONEncodedTest(RecipeTestMixin, unittest.TestCase):
  recipe = request.RequestJSONEncoded
  return_value_empty = "{}"
  return_value = '{"anything": "done"}'
  raises = True
  called_partition_parameter_kw = {'_': '{}'}


class RequestOptionalJSONEncodedTest(RecipeTestMixin, unittest.TestCase):
  recipe = request.RequestOptionalJSONEncoded
  return_value_empty = "{}"
  return_value = '{"anything": "done"}'
  raises = False
  called_partition_parameter_kw = {'_': '{}'}

class RecipejIOTestMixin:

  def setUp(self):
    self.buildout = {
      "buildout": {
      },
      "slap-connection": {
      }
    }
    self.parameter_dict = {"foo": "bar", "hello": "bye"}
    self.instance_data = {
      "reference": "SOFTINST-12",
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
      "parameters": json.dumps(self.parameter_dict),
      "connection_parameters": self.connection_parameter_dict,
    }
    self.options = {
      "server-url": "http://127.0.0.1:80",
      "name": self.instance_data["title"],
      "software-instance-reference": "SOFTINST-12",
      "computer-id": self.instance_data["compute_node_id"],
      "partition-id": self.instance_data["compute_partition_id"],
      "software-url": self.instance_data["software_release_uri"],
    }
    instance_root = tempfile.mkdtemp()
    partition_root = os.path.join(instance_root, self.instance_data["compute_partition_id"])
    os.mkdir(partition_root)
    os.environ['SLAPGRID_INSTANCE_ROOT'] = instance_root
    transaction_file_name = COMPUTER_PARTITION_REQUEST_LIST_TEMPLATE_FILENAME % self.instance_data["compute_partition_id"]
    self.transaction_file_path = os.path.join(partition_root,
                                             transaction_file_name)

  def test_no_return_in_options_logs(self):
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    with httmock.HTTMock(api_handler.request_handler):
      with LogCapture() as log:
        self.recipe(self.buildout, "request", self.options)
        log.check(
          ('request', 'DEBUG',
          'No parameter to return to main instance.Be careful about that...'),
        )
    expected_request_body = {
      "software_release_uri": "foo.cfg",
      "title": "MyInstance",
      "portal_type": "Software Instance",
      "compute_partition_id": "slappartx12",
      "state": "started",
      "compute_node_id": "COMP-321",
      "software_type": "RootSoftwareInstance"
    }
    if self.called_partition_parameter_kw:
      expected_request_body["parameters"] = json.dumps(self.called_partition_parameter_kw)
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps(expected_request_body))
    self.assertEqual(api_handler.sequence_list, ["/api/post/"])
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance'])

  def test_return_in_options_logs(self):
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    with httmock.HTTMock(api_handler.request_handler):
      with LogCapture() as log:
        self.recipe(self.buildout, "request", self.options)
        log.check()
    expected_request_body = {
      "software_release_uri": "foo.cfg",
      "title": "MyInstance",
      "portal_type": "Software Instance",
      "compute_partition_id": "slappartx12",
      "state": "started",
      "compute_node_id": "COMP-321",
      "software_type": "RootSoftwareInstance"
    }
    if self.called_partition_parameter_kw:
      expected_request_body["parameters"] = json.dumps(self.called_partition_parameter_kw)
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps(expected_request_body))
    self.assertEqual(self.options["connection-anything"], "done")
    self.assertEqual(api_handler.sequence_list, ["/api/post/"])
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance'])


  def test_return_not_ready(self):
    self.instance_data["connection_parameters"] = self.connection_parameter_dict_empty
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    with httmock.HTTMock(api_handler.request_handler):
      with LogCapture() as log:
        recipe = self.recipe(self.buildout, "request", self.options)
        log.check()

    if self.raises:
      self.assertRaises(KeyError, recipe.install)
    expected_request_body = {
      "software_release_uri": "foo.cfg",
      "title": "MyInstance",
      "portal_type": "Software Instance",
      "compute_partition_id": "slappartx12",
      "state": "started",
      "compute_node_id": "COMP-321",
      "software_type": "RootSoftwareInstance"
    }
    if self.called_partition_parameter_kw:
      expected_request_body["parameters"] = json.dumps(self.called_partition_parameter_kw)
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps(expected_request_body))
    self.assertEqual(self.options["connection-anything"], "")
    self.assertEqual(api_handler.sequence_list, ["/api/post/"])
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance'])

  def test_return_ready(self):
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.recipe(self.buildout, "request", self.options)
    result = recipe.install()
    self.assertEqual([], result)
    expected_request_body = {
      "software_release_uri": "foo.cfg",
      "title": "MyInstance",
      "portal_type": "Software Instance",
      "compute_partition_id": "slappartx12",
      "state": "started",
      "compute_node_id": "COMP-321",
      "software_type": "RootSoftwareInstance"
    }
    if self.called_partition_parameter_kw:
      expected_request_body["parameters"] = json.dumps(self.called_partition_parameter_kw)
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps(expected_request_body))
    self.assertEqual(self.options["connection-anything"], "done")
    self.assertIsInstance(self.options['connection-anything'], str)
    self.assertEqual(api_handler.sequence_list, ["/api/post/"])
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance'])

  def test_two_requests_return_ready(self):
    # Request first instance
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.recipe(self.buildout, "request", self.options)
    result = recipe.install()
    # Request Second Instance
    self.options["name"] = self.instance_data["title"] = 'MyInstance2'
    self.instance_data["reference"] = "SOFTINST-13"
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.recipe(self.buildout, "request", self.options)
    result = recipe.install()
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance', 'MyInstance2'])

  def test_requester_stopped_state_propagated(self):
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    self.buildout['slap-connection']['requested'] = 'stopped'
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.recipe(self.buildout, "request", self.options)
    result = recipe.install()
    self.assertEqual([], result)
    expected_request_body = {
      "software_release_uri": "foo.cfg",
      "title": "MyInstance",
      "portal_type": "Software Instance",
      "compute_partition_id": "slappartx12",
      "state": "stopped",
      "compute_node_id": "COMP-321",
      "software_type": "RootSoftwareInstance"
    }
    if self.called_partition_parameter_kw:
      expected_request_body["parameters"] = json.dumps(self.called_partition_parameter_kw)
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps(expected_request_body))
    self.assertEqual(self.options["connection-anything"], "done")
    self.assertIsInstance(self.options['connection-anything'], str)
    self.assertEqual(api_handler.sequence_list, ["/api/post/"])
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance'])

  def test_requester_destroyed_state_not_propagated(self):
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    self.options['return'] = 'anything'
    self.buildout['slap-connection']['requested'] = 'destroyed'
    with httmock.HTTMock(api_handler.request_handler):
      recipe = self.recipe(self.buildout, "request", self.options)
    result = recipe.install()
    self.assertEqual([], result)
    expected_request_body = {
      "software_release_uri": "foo.cfg",
      "title": "MyInstance",
      "portal_type": "Software Instance",
      "compute_partition_id": "slappartx12",
      "state": "started",
      "compute_node_id": "COMP-321",
      "software_type": "RootSoftwareInstance"
    }
    if self.called_partition_parameter_kw:
      expected_request_body["parameters"] = json.dumps(self.called_partition_parameter_kw)
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps(expected_request_body))
    self.assertEqual(self.options["connection-anything"], "done")
    self.assertIsInstance(self.options['connection-anything'], str)
    self.assertEqual(api_handler.sequence_list, ["/api/post/"])
    self.assertTrue(os.path.exists(self.transaction_file_path))
    with open(self.transaction_file_path, 'r') as f:
      content_list = f.read().splitlines()
      self.assertEqual(sorted(content_list), ['MyInstance'])

class RequestjIOTest(RecipejIOTestMixin, unittest.TestCase):
  recipe = request.Recipe
  connection_parameter_dict_empty = {}
  connection_parameter_dict = {"anything": "done"}
  called_partition_parameter_kw = None
  raises = True

class RequestjIOAPIOptionalTest(RecipejIOTestMixin, unittest.TestCase):
  recipe = request.RequestOptional
  connection_parameter_dict_empty = {}
  connection_parameter_dict = {"anything": "done"}
  called_partition_parameter_kw = None
  raises = False

class RequestjIOAPIJSONEncodedTest(RecipejIOTestMixin, unittest.TestCase):
  recipe = request.RequestJSONEncoded
  connection_parameter_dict_empty = {}
  connection_parameter_dict = {"_": '{"anything": "done"}'}
  called_partition_parameter_kw = {"_": "{}"}
  raises = True

class RequestjIOAPIOptionalJSONEncodedTest(RecipejIOTestMixin, unittest.TestCase):
  recipe = request.RequestOptionalJSONEncoded
  connection_parameter_dict_empty = {}
  connection_parameter_dict = {"_": '{"anything": "done"}'}
  called_partition_parameter_kw = {"_": "{}"}
  raises = False
