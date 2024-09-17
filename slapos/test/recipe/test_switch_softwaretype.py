from unittest.mock import MagicMock
import unittest
from slapos.recipe import switch_softwaretype
import zc.buildout.testing
from zc.buildout.buildout import MissingOption, MissingSection

class SwitchSoftwaretypeTest(unittest.TestCase):

  def setUp(self):
    self.buildout = buildout = zc.buildout.testing.Buildout()
    buildout['slap-configuration'] = {
        'slap-software-type': 'type1'
      }
    buildout['switch-softwaretype'] = {
        'recipe': 'slapos.cookbook:switch-softwaretype',
        'default': 'instance-default:output',
        'type1': 'instance-type1:output',
        'type2': 'instance-type2:output'
      }
    buildout['instance-default'] = {
        'recipe': 'slapos.recipe.template:jinja2',
        'output': 'instance-default.cfg'
      }
    buildout['instance-type1'] = {
        'recipe': 'slapos.recipe.template:jinja2',
        'output': 'instance-type1.cfg'
      }
    self.magick_sub_buildout = switch_softwaretype.SubBuildout = MagicMock()

  def install_recipe(self):
    switch_softwaretype.Recipe(
        self.buildout,
        'switch-softwaretype',
        self.buildout['switch-softwaretype'],
    ).install()

  def test_correct_type(self):
    self.install_recipe()
    self.magick_sub_buildout.assert_called_once()
    self.assertIn('instance-type1.cfg', self.magick_sub_buildout.call_args.args)

  def test_type_section_not_present(self):
    self.buildout['slap-configuration']['slap-software-type'] = 'type2'
    with self.assertRaises(MissingSection) as cm:
      self.install_recipe()
    self.magick_sub_buildout.assert_not_called()
    self.assertEqual('instance-type2', cm.exception.args[0])

  def test_type_not_present(self):
    self.buildout['slap-configuration']['slap-software-type'] = 'type3'
    with self.assertRaises(MissingOption) as cm:
      self.install_recipe()
    self.magick_sub_buildout.assert_not_called()
    self.assertIn("This software type (type3) isn't mapped", cm.exception.args[0])

  def test_fallback_default(self):
    self.buildout['slap-configuration']['slap-software-type'] = 'RootSoftwareInstance'
    with self.assertLogs('switch-softwaretype', level='INFO') as lc:
      self.install_recipe()
    self.magick_sub_buildout.assert_called_once()
    self.assertIn("The software_type 'RootSoftwareInstance' is deprecated", lc.output[0])
    self.assertIn('instance-default.cfg', self.magick_sub_buildout.call_args.args)
