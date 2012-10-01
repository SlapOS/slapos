# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
import unittest
from testERP5ComputerWithComputerModel import TestERP5ComputerWithComputerModel

class TestVifibComputerWithComputerModel(TestERP5ComputerWithComputerModel):
  pass

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibComputerWithComputerModel))
  return suite
