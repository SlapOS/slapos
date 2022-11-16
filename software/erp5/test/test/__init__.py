##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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

import json
import os
import sys

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


_setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'test.cfg')))


setup_module_executed = False
def setUpModule():
  # slapos.testing.testcase's only need to be executed once
  global setup_module_executed
  if not setup_module_executed:
    _setUpModule()
  setup_module_executed = True


class ERP5InstanceTestMeta(type):
  """ERP5InstanceTestMeta adjusts instances of ERP5InstanceTestCase to
     be run in several flavours: with ZEO and with NEO. Adjustment
     of individual classes can be deactivated by setting the class
     attribute '__parameterize__' to 'False'.
  """

  def __new__(cls, name, bases, attrs):
    base_class = super().__new__(cls, name, bases, attrs)
    if base_class._isParameterized():
      cls._parameterize(base_class)
    return base_class

  # Create two test classes from single definition: e.g. TestX -> TestX_ZEO and TestX_NEO.
  @classmethod
  def _parameterize(cls, base_class):
    test_class_module = sys.modules[base_class.__module__].__dict__
    for flavour in ("zeo", "neo"):
      # Override metaclass to avoid infinite loop due to parameterized
      # class which infinitely creates a parameterized class of itself.
      class patched(base_class, metaclass=_deactivate):
        zodb_storage = flavour

      # Switch
      #   - .getInstanceParameterDict       to ._test_getInstanceParameterDict, and
      #   - ._base_getInstanceParameterDict to .getInstanceParameterDict
      # so that we could inject base implementation to be called above user-defined getInstanceParameterDict.
      # see ERP5InstanceTestCase._base_getInstanceParameterDict for details.
      patched._test_getInstanceParameterDict = patched.getInstanceParameterDict
      patched.getInstanceParameterDict       = patched._base_getInstanceParameterDict

      name = "%s_%s" % (base_class.__name__, flavour.upper())
      test_class_module[name] = type(name, (patched,), dict(patched.__dict__))

  # Hide tests in patched class.
  # We can't simply call 'delattr', because this wouldn't remove
  # inherited tests. Overriding dir is sufficient, because this is
  # the way how unittest discovers tests:
  #   https://github.com/python/cpython/blob/3.11/Lib/unittest/loader.py#L237
  def __dir__(self):
    if self._isParameterized():
      return [attr for attr in super().__dir__() if not attr.startswith('test')]
    return super().__dir__()

  def _isParameterized(self):
    return getattr(self, '__parameterize__', True)


class _deactivate(ERP5InstanceTestMeta):
  """_deactivate behaves exactly the same like plain type.

  It allows the syntax

    >>> class A(metaclass=ERP5InstanceTestMeta): ...
    >>> class B(A, metaclass=_deactivate): ...

  to deactivate ERP5InstanceTestMeta in a subclass of A.
  """
  def __new__(cls, name, bases, attrs):
    return type.__new__(cls, name, bases, attrs)

  def __dir__(self):
    return type.__dir__(self)


class ERP5InstanceTestCase(SlapOSInstanceTestCase, metaclass=ERP5InstanceTestMeta):
  """ERP5 base test case
  """

  # ERP5InstanceTestMeta switches:
  #   - _base_getInstanceParameterDict to be real getInstanceParameterDict, while
  #   - test-defined getInstanceParameterDict is switched to _test_getInstanceParameterDict
  # here we invoke user-defined getInstanceParameterDict and adjust it according to "zodb_storage" parameter.
  @classmethod
  def _base_getInstanceParameterDict(cls):
      try:
        parameter_dict = json.loads(cls._test_getInstanceParameterDict()["_"])
      except KeyError:
        parameter_dict = {}
      server = {"ssl": False} if cls.zodb_storage == "neo" else {}
      parameter_dict["zodb"] = [{"type": cls.zodb_storage, "server": server}]
      return {"_": json.dumps(parameter_dict)}

  @classmethod
  def getRootPartitionConnectionParameterDict(cls):
    """Return the output paramters from the root partition"""
    return json.loads(
        cls.computer_partition.getConnectionParameterDict()['_'])

  @classmethod
  def getComputerPartition(cls, partition_reference):
    for computer_partition in cls.slap.computer.getComputerPartitionList():
      if partition_reference == computer_partition.getInstanceParameter(
          'instance_title'):
        return computer_partition

  @classmethod
  def getComputerPartitionPath(cls, partition_reference):
    partition_id = cls.getComputerPartition(partition_reference).getId()
    return os.path.join(cls.slap._instance_root, partition_id)
