import os
import sys
import unittest

from tempfile import mkdtemp
from shutil import rmtree

class TestGenericCloudooo(unittest.TestCase):
  def new_recipe(self, options):
    from slapos.recipe import generic_cloudooo
    from slapos.test.utils import makeRecipe
    return makeRecipe(
        generic_cloudooo.Recipe,
        options=options,
        name='generic_cloudooo')

  def setUp(self):
    self.test_dir = mkdtemp()
  def tearDown(self):
    if os.path.exists(self.test_dir):
      rmtree(self.test_dir)

  def test_install(self):
    # Basic check
    config_file_path = os.path.join(self.test_dir, "test_install_configuration_file_etc_cloudooo-X.cfg")
    recipe = self.new_recipe({
      "ip": "test_install_ip",
      "environment": "test_install=environment",
      "mimetype_entry_addition": "text/install mimetype/entry addition",
      "ooo-binary-path": "test_install_ooo_binary_path",
      "ooo-paster": "test_install_ooo_paster",
      "ooo-uno-path": "test_ooo_uno_path",
      "port": "123",
      "openoffice-port": "234",
      "configuration-file": config_file_path,
      "data-directory": os.path.join(self.test_dir, "test_install_data_directory_srv_cloudooo-X"),
      "wrapper": os.path.join(self.test_dir, "test_install_wrapper_service_cloudooo-X"),
    })
    recipe.install()
    data = open(config_file_path).read()
    self.assertIn("[app:main]", data)
    self.assertIn("[server:main]", data)

    # Check if mimetype_registry is well ordered
    self.assertIn("\n  text/install mimetype/entry addition\n  text/* * ooo\n", data)

    # Check OnlyOffice entries
    self.assertIn("\n".join([
      "",
      "  application/vnd.openxmlformats-officedocument.presentationml.presentation application/x-asc-presentation x2t",
      "  application/vnd.openxmlformats-officedocument.spreadsheetml.sheet application/x-asc-spreadsheet x2t",
      "  application/vnd.openxmlformats-officedocument.wordprocessingml.document application/x-asc-text x2t",
      "",
    ]), data)
    self.assertIn("\n".join([
      "",
      "  application/x-asc-presentation application/vnd.oasis.opendocument.presentation x2t",
      "  application/x-asc-presentation application/vnd.openxmlformats-officedocument.presentationml.presentation x2t",
      "  application/x-asc-spreadsheet application/vnd.oasis.opendocument.spreadsheet x2t",
      "  application/x-asc-spreadsheet application/vnd.openxmlformats-officedocument.spreadsheetml.sheet x2t",
      "  application/x-asc-text application/vnd.oasis.opendocument.text x2t",
      "  application/x-asc-text application/vnd.openxmlformats-officedocument.wordprocessingml.document x2t",
      "",
    ]), data)
