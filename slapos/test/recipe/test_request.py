import mock
import unittest
from collections import defaultdict
from slapos.recipe import request
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
