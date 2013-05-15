from test_suite import SavedTestSuite, ProjectTestSuite

slapos_bt_list = [
    'erp5_web_shacache',
    'erp5_web_shadir',
    'slapos_accounting',
    'slapos_cache',
    'slapos_cloud',
    'slapos_erp5',
    'slapos_pdm',
    'slapos_rest_api',
    'slapos_slap_tool',
    'slapos_hypermedia',
    'slapos_web',
    'slapos_crm',
    'slapos_payzen',
  ]

class SlapOSCloud(SavedTestSuite, ProjectTestSuite):
  _product_list = ['SlapOS']
  _saved_test_id = 'Products.SlapOS.tests.testSlapOSMixin.testSlapOSMixin'
  _bt_list = slapos_bt_list

  def __init__(self, max_instance_count=1, *args, **kw):
    # hardcode number of node, to prevent concurrency issue on certificate
    # authority file system storage
    super(SlapOSCloud, self).__init__(max_instance_count=1, *args, **kw)
