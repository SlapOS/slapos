from test_suite import SavedTestSuite, ProjectTestSuite

class VIFIB(SavedTestSuite, ProjectTestSuite):
  _product_list = ['Vifib']
  _saved_test_id = 'Products.Vifib.tests.VifibMixin.testVifibMixin'
  _bt_list = [
    'slapos_cloud',
    'slapos_rest_api',
    'vifib_base',
    'vifib_data',
    'slapos_category',
    'vifib_data_web',
    'slapos_erp5',
    'vifib_erp5',
    'vifib_slap',
    'vifib_upgrader',
    'vifib_web',
  ]

class SlapOSCloud(SavedTestSuite, ProjectTestSuite):
  _product_list = ['SlapOS']
  _saved_test_id = 'Products.SlapOS.tests.testSlapOSMixin.testSlapOSMixin'
  _bt_list = [
    'slapos_cloud',
    'slapos_cache',
    'slapos_erp5',
    'slapos_pdm',
    'slapos_subscription',
    'slapos_slap_tool',
    'slapos_rest_api',
    'erp5_web_shadir',
    'erp5_web_shacache',
  ]
