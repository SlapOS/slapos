from test_suite import SavedTestSuite, ProjectTestSuite

class VIFIB(SavedTestSuite, ProjectTestSuite):
  _product_list = ['Vifib']
  _saved_test_id = 'Products.Vifib.tests.VifibMixin.testVifibMixin'
  _bt_list = [
    'vifib_slapos_core',
    'vifib_slapos_core_test',
    'vifib_slapos_rest_api',
    'vifib_slapos_rest_api_v1',
    'vifib_slapos_rest_api_tool_portal_type',
    'vifib_slapos_rest_api_v1_test',
    'vifib_base',
    'vifib_core',
    'vifib_data',
    'vifib_data_category',
    'vifib_data_web',
    'vifib_erp5',
    'vifib_forge_release',
    'vifib_l10n_fr',
    'vifib_mysql_innodb_catalog',
    'vifib_open_trade',
    'vifib_slap',
    'vifib_software_pdm',
    'vifib_upgrader',
    'vifib_web',
  ]
