# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################
import unittest
from SlapOSMixin import testSlapOSMixin

class TestSlapOSDummy(testSlapOSMixin):
  run_all_test = 1
  def test(self):
    self.assertTrue(True)

  def getTitle(self):
    return "Dummy tests in order to have tests from BT5 run"

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapOSDummy))
  return suite
