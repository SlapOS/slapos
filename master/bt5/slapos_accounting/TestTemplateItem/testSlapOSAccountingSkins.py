# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin, withAbort

class TestSlapOSAccounting(testSlapOSMixin):
  @withAbort
  def test_Service_getPriceCalculationOperandDict(self):
    service = self.portal.service_module.newContent(portal_type='Service')
    self.assertEqual({'price': 0.0},
        service.Service_getPriceCalculationOperandDict())
