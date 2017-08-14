from test_suite import SavedTestSuite, ProjectTestSuite
from glob import glob
import os, re
import sys

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
    'slapos_web',
    'slapos_crm',
    'slapos_payzen',
    'slapos_configurator',
    'slapos_jio'
  ]

class SlapOSCloud(SavedTestSuite, ProjectTestSuite):
  _product_list = ['SlapOS']
  _saved_test_id = 'Products.SlapOS.tests.testSlapOSMixin.testSlapOSMixin'
  _bt_list = slapos_bt_list
  
  def getTestList(self):
    test_list = []
    path = sys.path[0]
    erp5_path = sys.path[1]
    component_re = re.compile(".*/([^/]+)/TestTemplateItem/portal_components"
                              "/test\.[^.]+\.([^.]+).py$")
    for test_path in (
        glob('%s/product/*/tests/test*.py' % path) +
        glob('%s/bt5/*/TestTemplateItem/test*.py' % path) +
        glob('%s/bt5/*/TestTemplateItem/portal_components/test.*.test*.py' % path) +
        glob('%s/bt5/*/TestTemplateItem/test*.py' % erp5_path) +
        glob('%s/bt5/*/TestTemplateItem/portal_components/test.*.test*.py' % erp5_path)):
      component_re_match = component_re.match(test_path)
      if component_re_match is not None:
        test_case = "%s:%s" % (component_re_match.group(1),
                               component_re_match.group(2))
      else:
        test_case = test_path.split(os.sep)[-1][:-3] # remove .py
      # Filter bt tests to run from _bt_list list
      if test_path.split(os.sep)[-2] != 'tests':
        if test_path.split(os.sep)[-2] == 'portal_components':
          product = test_path.split(os.sep)[-4]
        else:
          product = test_path.split(os.sep)[-3]
        if not product in self._bt_list:
          continue
      elif test_path.split(os.sep)[-3] == 'Vifib':
        # There is no valid tests in Vifib!
        continue
      test_list.append(test_case)
    return test_list

  def __init__(self, max_instance_count=1, *args, **kw):
    # hardcode number of node, to prevent concurrency issue on certificate
    # authority file system storage
    super(SlapOSCloud, self).__init__(max_instance_count=1, *args, **kw)
