# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#                    Łukasz Nowak <luke@nexedi.com>
#                    Romain Courteaud <romain@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import unittest
from VifibMixin import testVifibMixin
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from slapos.slap.tests import testinterface
# from slapos.slap.tests import testslap

"""Test to check slap in ERP5 test runner

Some tests are just wrapping slap egg in ERP5TypeTestCase

Others are using generated site with data and use such site as server to test
slap as client library.
"""

class VifibServerMixin(testVifibMixin):
  def afterSetUp(self):
    testVifibMixin.afterSetUp(self)
    self.server_url = self.portal.portal_slap.absolute_url()

class TestSlapInterface(ERP5TypeTestCase, testinterface.TestInterface):
  """Wrapper class for TestInterface

  Note: This is here because there is no test runner for eggs."""

# class TestSlapSlap(testVifibMixin, testslap.TestSlap):
#   """Wrapper class for TestSlap"""
# 
# class TestSlapComputer(VifibServerMixin, testslap.TestComputer):
#   """Wrapper class for TestComputer"""
# 
# class TestSlapComputerPartition(VifibServerMixin,
#     testslap.TestComputerPartition):
#   """Wrapper class for TestComputerPartition"""
# 
# class TestSlapSoftwareRelease(VifibServerMixin,
#     testslap.TestSoftwareRelease):
#   """Wrapper class for TestSoftwareRelease"""
# 
# class TestSlapOpenOrder(VifibServerMixin,
#     testslap.TestOpenOrder):
#   """Wrapper class for TestSoftwareRelease"""

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSlapInterface))
#   suite.addTest(unittest.makeSuite(TestSlapSlap))
#   suite.addTest(unittest.makeSuite(TestSlapComputer))
#   suite.addTest(unittest.makeSuite(TestSlapComputerPartition))
#   suite.addTest(unittest.makeSuite(TestSlapSoftwareRelease))
#   suite.addTest(unittest.makeSuite(TestSlapOpenOrder))
  return suite
