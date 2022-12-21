##############################################################################
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
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
        os.path.join(os.path.dirname(__file__), '..', '..', 'software.cfg')))


setup_module_executed = False
def setUpModule():
  # slapos.testing.testcase's only need to be executed once
  global setup_module_executed
  if not setup_module_executed:
    _setUpModule()
  setup_module_executed = True


# Metaclass to parameterize our tests.
# This is a rough adaption of the parameterized package:
#   https://github.com/wolever/parameterized
# Consult following note for rationale why we don't use parameterized:
#   https://lab.nexedi.com/nexedi/slapos/merge_requests/1306
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

  # _isParameterized tells whether class is parameterized.
  # A user-defined class with .__parameterize__ = True is considered
  # to be parameterized.
  # But classes automatically instantiated from such user class with
  # particular parameters are considered to be not parameterized.
  def _isParameterized(self):
    return (
      getattr(self, '__parameterize__', True) and
      not getattr(self, '.created_by_parametrize', False)
    )

  # Create two test classes from single definition: e.g. TestX -> TestX_ZEO and TestX_NEO.
  @classmethod
  def _parameterize(cls, base_class):
    mod_dict = sys.modules[base_class.__module__].__dict__
    for flavour in ("zeo", "neo"):
      patched_cls_dict = dict(base_class.__dict__)        # dict for flavoured class
      patched_cls_dict['.created_by_parametrize'] = True  # prevent infinite recursion
      patched_cls_dict['zodb_storage'] = flavour

      name = "%s_%s" % (base_class.__name__, flavour.upper())
      patched = type(name, (base_class,), patched_cls_dict)

      # Switch
      #   - .getInstanceParameterDict       to ._test_getInstanceParameterDict, and
      #   - ._base_getInstanceParameterDict to .getInstanceParameterDict
      # so that we could inject base implementation to be called above user-defined getInstanceParameterDict.
      # see ERP5InstanceTestCase._base_getInstanceParameterDict for details.
      patched._test_getInstanceParameterDict = patched.getInstanceParameterDict
      patched.getInstanceParameterDict       = patched._base_getInstanceParameterDict

      mod_dict[name] = patched

  # Hide tests in unpatched base class: It doesn't make sense to run tests
  # in original class, because parameters have not been assigned yet.
  #
  # We can't simply call 'delattr', because this wouldn't remove
  # inherited tests. Overriding dir is sufficient, because this is
  # the way how unittest discovers tests:
  #   https://github.com/python/cpython/blob/3.11/Lib/unittest/loader.py#L237
  def __dir__(self):
    if self._isParameterized():
      return [attr for attr in super().__dir__() if not attr.startswith('test')]
    return super().__dir__()


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
      # We don't provide encryption certificates in test runs for the sake
      # of simplicity. By default SSL is turned on, we need to explicitly
      # deactivate it:
      #   https://lab.nexedi.com/nexedi/slapos/blob/a8150a1ac/software/neoppod/instance-neo-input-schema.json#L61-65
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
