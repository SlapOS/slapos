# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import os
from Testing import ZopeTestCase

class TestSlapOSDump(testSlapOSMixin):
  def write(self, name, output):
    path = os.path.join(os.environ['INSTANCE_HOME'], name)
    with open(path, 'w') as f:
      f.write(output)
    return path

  def test(self):
    issue_count = 0
    for dump in [
        'ERP5Site_dumpAlarmToolConfiguration',
        'ERP5Site_dumpBuilderList',
        'ERP5Site_dumpInstalledBusinessTemplateList',
        'ERP5Site_dumpOrderBuilderList',
        'ERP5Site_dumpPortalTypeActionList',
        'ERP5Site_dumpPortalTypeList',
        'ERP5Site_dumpPortalTypeRoleList',
        'ERP5Site_dumpPropertySheetList',
        'ERP5Site_dumpRuleTesterList',
        'ERP5Site_dumpSkinProperty',
        'ERP5Site_dumpWorkflowChain',
      ]:
      ZopeTestCase._print('\n')
      try:
        location = self.write('%s.txt' % dump, getattr(self.portal, dump)())
      except Exception:
        ZopeTestCase._print('Problem with %s\n' % dump)
        issue_count += 1
      else:
        ZopeTestCase._print('Stored dump %s in %s\n' % (dump, location))
    self.assertEqual(0, issue_count)
