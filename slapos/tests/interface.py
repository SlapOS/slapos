##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
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

from zope.interface.verify import verifyClass
import zope.interface
import types
from slapos import slap

def getOnlyImplementationAssertionMethod(klass, method_list):
  """Returns method which verifies if a klass only implements its interfaces"""
  def testMethod(self):
    implemented_method_list = [x for x in dir(klass) \
        if ((not x.startswith('_')) and callable(getattr(klass, x)))]
    for interface_method in method_list:
      if interface_method in implemented_method_list:
        implemented_method_list.remove(interface_method)

    if implemented_method_list:
      raise AssertionError("Unexpected methods %s" % implemented_method_list)
  return testMethod

def getImplementationAssertionMethod(klass, interface):
  """Returns method which verifies if interface is properly implemented by klass"""
  def testMethod(self):
    verifyClass(interface, klass)
  return testMethod

def getDeclarationAssertionMethod(klass):
  """Returns method which verifies if klass is declaring interface"""
  def testMethod(self):
    if len(list(zope.interface.implementedBy(klass))) == 0:
      self.fail('%s class does not respect its interface(s).' % klass.__name__)
  return testMethod

def generateTestMethodListOnClass(klass, module):
  """Generate test method on klass"""
  for class_id in dir(module):
    implementing_class = getattr(module, class_id)
    if type(implementing_class) not in (types.ClassType, types.TypeType):
      continue
    # add methods to assert that publicly available classes are defining
    # interfaces
    method_name = 'test_%s_declares_interface' % (class_id,)
    setattr(klass, method_name, getDeclarationAssertionMethod(
      implementing_class))

    implemented_method_list = []
    for interface in list(zope.interface.implementedBy(implementing_class)):
      # for each interface which class declares add a method which verify
      # implementation
      method_name = 'test_%s_implements_%s' % (class_id,
          interface.__identifier__)
      setattr(klass, method_name, getImplementationAssertionMethod(
        implementing_class, interface))

      for interface_klass in interface.__iro__:
        implemented_method_list.extend(interface_klass.names())

    # for each interface which class declares, check that no other method are
    # available
    method_name = 'test_%s_only_implements' % class_id
    setattr(klass, method_name, getOnlyImplementationAssertionMethod(
      implementing_class,
      implemented_method_list))

class TestInterface(unittest.TestCase):
  """Tests all publicly available classes of slap

  Classes are checked *if* they implement interface and if the implementation
  is correct.
  """

# add methods to test class
generateTestMethodListOnClass(TestInterface, slap)

if __name__ == '__main__':
  unittest.main()
