import httmock
import json
import mock
import unittest
from collections import defaultdict
from slapos.recipe import request
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

  def test_no_return_in_options_logs(self):
    api_handler = APIRequestHandler([
      ("/api/get", json.dumps(self.instance_data)),
    ])
    with httmock.HTTMock(api_handler.request_handler):
      with LogCapture() as log:
      #import pdb; pdb.set_trace()
        self.recipe(self.buildout, "request", self.options)
        log.check(
          ('request', 'DEBUG',
          'No parameter to return to main instance.Be careful about that...'),
        )
    self.assertEqual(
      api_handler.request_payload_list[0], json.dumps({
        "software_release_uri": "foo.cfg",
        "title": "MyInstance",
        "portal_type": "Software Instance",
        "compute_partition_id": "slappartx12",
        "state": "started",
        "compute_node_id": "COMP-321",
        "software_type": "RootSoftwareInstance"
      }))

  def test_return_in_options_logs(self):
    pass

  def test_return_not_ready(self):
    pass

  def test_return_ready(self):
    pass

class RequestjIOTest(RecipejIOTestMixin, unittest.TestCase):
  recipe = request.Recipe
  connection_parameter_dict_empty = {}
  connection_parameter_dict = {"foo": "bar"}
