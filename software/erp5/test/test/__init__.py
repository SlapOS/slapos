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

import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from slapos.testing.testcase import ManagedResource, makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import findFreeTCPPort


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
  def isNEO(cls):
    return '_neo' in cls.__name__

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


class CaucaseService(ManagedResource):
  """A caucase service.
  """
  url: str = None
  directory: str = None
  _caucased_process: subprocess.Popen = None

  def open(self) -> None:
    # start a caucased and server certificate.
    software_release_root_path = os.path.join(
        self._cls.slap._software_root,
        hashlib.md5(self._cls.getSoftwareURL().encode()).hexdigest(),
    )
    caucased_path = os.path.join(software_release_root_path, 'bin', 'caucased')

    self.directory = tempfile.mkdtemp()
    caucased_dir = os.path.join(self.directory, 'caucased')
    os.mkdir(caucased_dir)
    os.mkdir(os.path.join(caucased_dir, 'user'))
    os.mkdir(os.path.join(caucased_dir, 'service'))

    backend_caucased_netloc = f'{self._cls._ipv4_address}:{findFreeTCPPort(self._cls._ipv4_address)}'
    self.url = 'http://' + backend_caucased_netloc
    self._caucased_process = subprocess.Popen(
        [
            caucased_path,
            '--db', os.path.join(caucased_dir, 'caucase.sqlite'),
            '--server-key', os.path.join(caucased_dir, 'server.key.pem'),
            '--netloc', backend_caucased_netloc,
            '--service-auto-approve-count', '1',
        ],
        # capture subprocess output not to pollute test's own stdout
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for _ in range(30):
      try:
        if requests.get(self.url).status_code == 200:
          break
      except Exception:
        pass
      time.sleep(1)
    else:
      raise RuntimeError('caucased failed to start.')

  def close(self) -> None:
    self._caucased_process.terminate()
    self._caucased_process.wait()
    self._caucased_process.stdout.close()
    shutil.rmtree(self.directory)

  @property
  def ca_crt_path(self) -> str:
    """Path of the CA certificate from this caucase.
    """
    ca_crt_path = os.path.join(self.directory, 'ca.crt.pem')
    if not os.path.exists(ca_crt_path):
      with open(ca_crt_path, 'w') as f:
        f.write(
            requests.get(urllib.parse.urljoin(
                self.url,
                '/cas/crt/ca.crt.pem',
            )).text)
    return ca_crt_path



class CaucaseCertificate(ManagedResource):
  """A certificate signed by a caucase service.
  """

  ca_crt_file: str = None
  crl_file: str = None
  csr_file: str = None
  cert_file: str = None
  key_file: str = None

  def open(self) -> None:
    self.tmpdir = tempfile.mkdtemp()
    self.ca_crt_file = os.path.join(self.tmpdir, 'ca-crt.pem')
    self.crl_file = os.path.join(self.tmpdir, 'ca-crl.pem')
    self.csr_file = os.path.join(self.tmpdir, 'csr.pem')
    self.cert_file = os.path.join(self.tmpdir, 'crt.pem')
    self.key_file = os.path.join(self.tmpdir, 'key.pem')

  def close(self) -> None:
    shutil.rmtree(self.tmpdir)

  @property
  def _caucase_path(self) -> str:
    """path of caucase executable.
    """
    software_release_root_path = os.path.join(
        self._cls.slap._software_root,
        hashlib.md5(self._cls.getSoftwareURL().encode()).hexdigest(),
    )
    return os.path.join(software_release_root_path, 'bin', 'caucase')

  def request(self, common_name: str, caucase: CaucaseService, san: x509.SubjectAlternativeName=None) -> None:
    """Generate certificate and request signature to the caucase service.

    This overwrite any previously requested certificate for this instance.
    """
    cas_args = [
        self._caucase_path,
        '--ca-url', caucase.url,
        '--ca-crt', self.ca_crt_file,
        '--crl', self.crl_file,
    ]

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    with open(self.key_file, 'wb') as f:
      f.write(
          key.private_bytes(
              encoding=serialization.Encoding.PEM,
              format=serialization.PrivateFormat.TraditionalOpenSSL,
              encryption_algorithm=serialization.NoEncryption(),
          ))

    csr = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([
            x509.NameAttribute(
                NameOID.COMMON_NAME,
                common_name,
            ),
        ]))
    if san:
      csr = csr.add_extension(san, critical=True)
    csr = csr.sign(key, hashes.SHA256(), default_backend())
    with open(self.csr_file, 'wb') as f:
      f.write(csr.public_bytes(serialization.Encoding.PEM))

    csr_id = subprocess.check_output(
      cas_args + [
          '--send-csr', self.csr_file,
      ],
    ).split()[0].decode()
    assert csr_id

    for _ in range(30):
      if not subprocess.call(
        cas_args + [
            '--get-crt', csr_id, self.cert_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
      ) == 0:
        break
      else:
        time.sleep(1)
    else:
      raise RuntimeError('getting service certificate failed.')
    with open(self.cert_file) as cert_file:
      assert 'BEGIN CERTIFICATE' in cert_file.read()

  def revoke(self, caucase: CaucaseService) -> None:
    """Revoke the client certificate on this caucase instance.
    """
    subprocess.check_call([
        self._caucase_path,
        '--ca-url', caucase.url,
        '--ca-crt', self.ca_crt_file,
        '--crl', self.crl_file,
        '--revoke-crt', self.cert_file, self.key_file,
    ])
