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

import itertools
import json
import os
import sys

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass


_setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'software%s.cfg' % (
          '-py3' if os.environ['SLAPOS_SR_TEST_NAME'] == 'erp5-py3' else ''))))


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
  """Adjust ERP5InstanceTestCase instances to be run in several flavours (e.g. NEO/ZEO)

  Adjustments can be declared via setting the '__test_matrix__' attribute
  of a test case.
  A test matrix is a dict which maps the flavoured class name suffix to
  a tuple of parameters.
  A parameter is a function which receives the instance_parameter_dict
  and modifies it in place (therefore no return value is needed).
  You can use the 'matrix' helper function to construct a test matrix.
  If .__test_matrix__ is 'None' the test case is ignored.
  If the test case should be run without any adaptions, you can set
  .__test_matrix__ to 'matrix((default,))'.
  """

  def __new__(cls, name, bases, attrs):
    base_class = super().__new__(cls, name, bases, attrs)
    if base_class._isParameterized():
      cls._parameterize(base_class)
    return base_class

  # _isParameterized tells whether class is parameterized.
  # All classes with 'metaclass=ERP5InstanceTestMeta' are parameterized
  # except from a class which has been automatically instantiated from
  # such user class. This exception prevents infinite recursion due to
  # a parameterized class which tries to parameterize itself again.
  def _isParameterized(self):
    return not getattr(self, '.created_by_parametrize', False)

  # Create multiple test classes from single definition.
  @classmethod
  def _parameterize(cls, base_class):
    mod_dict = sys.modules[base_class.__module__].__dict__
    for class_name_suffix, parameter_tuple in (base_class.__test_matrix__ or {}).items():
      parameterized_cls_dict = dict(
        base_class.__dict__,
        **{
          # Avoid infinite loop by a parameterized class which
          # parameterize itself again and again and..
          ".created_by_parametrize": True,
          # Switch
          #
          #  .getInstanceParameterDict       to ._test_getInstanceParameterDict
          #  ._base_getInstanceParameterDict to .getInstanceParameterDict
          #
          # so that we could inject base implementation to be called above
          # user-defined getInstanceParameterDict.
          "_test_getInstanceParameterDict": base_class.getInstanceParameterDict,
          "getInstanceParameterDict": cls._getParameterizedInstanceParameterDict(parameter_tuple)
        }
      )
      name = f"{base_class.__name__}_{class_name_suffix}"
      mod_dict[name] = type(name, (base_class,), parameterized_cls_dict)

  # _getParameterizedInstanceParameterDict returns a modified version of
  # a test cases original 'getInstanceParameterDict'. The modified version
  # applies parameters on the default instance parameters.
  @staticmethod
  def _getParameterizedInstanceParameterDict(parameter_tuple):
    @classmethod
    def getInstanceParameterDict(cls):
      instance_parameter_dict = json.loads(
        cls._test_getInstanceParameterDict().get("_", r"{}")
      )
      [p(instance_parameter_dict) for p in parameter_tuple]
      return {"_": json.dumps(instance_parameter_dict)}
    return getInstanceParameterDict

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


def matrix(*parameter_tuple):
  """matrix creates a mapping of test_name -> parameter_tuple.

  Each provided parameter_tuple won't be combined within itself,
  but with any other provided parameter_tuple, for instance

    >>> parameter_tuple0 = (param0, param1)
    >>> parameter_tuple1 = (param2, param3)
    >>> matrix(parameter_tuple0, parameter_tuple1)

  will return all options of (param0 | param1) & (param2 | param3):

    - param0_param2
    - param0_param3
    - param1_param2
    - param1_param3
  """
  return {
    "_".join([p.__name__ for p in params]): params
    for params in itertools.product(*parameter_tuple)
  }


# Define parameters (function which receives instance params + modifies them).
#
# default runs tests without any adaption
def default(instance_parameter_dict): ...


def zeo(instance_parameter_dict):
  instance_parameter_dict['zodb'] = [{"type": "zeo", "server": {}}]


def neo(instance_parameter_dict):
   # We don't provide encryption certificates in test runs for the sake
  # of simplicity. By default SSL is turned on, we need to explicitly
  # deactivate it:
  #   https://lab.nexedi.com/nexedi/slapos/blob/a8150a1ac/software/neoppod/instance-neo-input-schema.json#L61-65
  instance_parameter_dict['zodb'] = [{"type": "neo", "server": {"ssl": False}}]


class ERP5InstanceTestCase(SlapOSInstanceTestCase, metaclass=ERP5InstanceTestMeta):
  """ERP5 base test case
  """
  __test_matrix__ = matrix((zeo, neo))  # switch between NEO and ZEO mode

  @classmethod
  def getRootPartitionConnectionParameterDict(cls):
    """Return the output parameters from the root partition"""
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
