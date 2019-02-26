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

import unittest
import os
import socket
from contextlib import closing
import logging
import StringIO
import xmlrpclib
import signal

import supervisor.xmlrpc
from erp5.util.testnode.SlapOSControler import SlapOSControler
from erp5.util.testnode.ProcessManager import ProcessManager


SLAPOS_PROXY_PORT = 43880

# Utility functions
def findFreeTCPPort(ip=''):
  """Find a free TCP port to listen to.
  """
  family = socket.AF_INET6 if ':' in ip else socket.AF_INET
  with closing(socket.socket(family, socket.SOCK_STREAM)) as s:
    s.bind((ip, 0))
    return s.getsockname()[1]


# TODO:
#  - allow requesting multiple instances ?

class SlapOSInstanceTestCase(unittest.TestCase):
  """Install one slapos instance.

  This test case install software(s) and request one instance during `setUpClass`
  and destroy the instance during `tearDownClass`.

  Software Release URL, Instance Software Type and Instance Parameters can be defined
  on the class.

  All tests from the test class will run with the same instance.

  The following class attributes are available:

    * `computer_partition`:  the computer partition instance, implementing
    `slapos.slap.interface.slap.IComputerPartition`.

    * `computer_partition_root_path`: the path of the instance root directory.

  """

  # Methods to be defined by subclasses.
  @classmethod
  def getSoftwareURLList(cls):
    """Return URL of software releases to install.

    To be defined by subclasses.
    """
    raise NotImplementedError()

  @classmethod
  def getInstanceParameterDict(cls):
    """Return instance parameters

    To be defined by subclasses if they need to request instance with specific
    parameters.
    """
    return {}

  @classmethod
  def getInstanceSoftwareType(cls):
    """Return software type for instance, default "default"

    To be defined by subclasses if they need to request instance with specific
    software type.
    """
    return "default"

  # Utility methods.
  def getSupervisorRPCServer(self):
    """Returns a XML-RPC connection to the supervisor used by slapos node

    Refer to http://supervisord.org/api.html for details of available methods.
    """
    # xmlrpc over unix socket https://stackoverflow.com/a/11746051/7294664
    return xmlrpclib.ServerProxy(
       'http://slapos-supervisor',
       transport=supervisor.xmlrpc.SupervisorTransport(
           None,
           None,
           # XXX hardcoded socket path
           serverurl="unix://{working_directory}/inst/supervisord.socket".format(
             **self.config)))

  # Unittest methods
  @classmethod
  def setUpClass(cls):
    """Setup the class, build software and request an instance.

    If you have to override this method, do not forget to call this method on
    parent class.
    """
    try:
      cls.setUpWorkingDirectory()
      cls.setUpConfig()
      cls.setUpSlapOSController()

      cls.runSoftwareRelease()
      # XXX instead of "runSoftwareRelease", it would be better to be closer to slapos usage:
      # cls.supplySoftwares()
      # cls.installSoftwares()

      cls.runComputerPartition()
      # XXX instead of "runComputerPartition", it would be better to be closer to slapos usage:
      # cls.requestInstances()
      # cls.createInstances()
      # cls.requestInstances()

    except Exception:
      cls.stopSlapOSProcesses()
      raise

  @classmethod
  def tearDownClass(cls):
    """Tear down class, stop the processes and destroy instance.
    """
    cls.stopSlapOSProcesses()

  @classmethod
  def stopSupervisorGracefully(cls):
    timeout = 10

    def stopSupervisor():
      # stop supervisor nicely
      while True:
        try:
          cls.getSupervisorRPCServer().supervisor.shutdown()
        except Exception:
          break

    def timeout_handler():
      try:
        cls.getSupervisorRPCServer().supervisor.shutdown()
      except Exception:
        pass
      else:
        try:
          state = cls.getSupervisorRPCServer().supervisor.getState()
        except Exception as e:
          state = e
        raise ValueError('After %ss supervisor still in state %r' (
          timeout, state))

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    stopSupervisor()

  # Implementation
  @classmethod
  def stopSlapOSProcesses(cls):
    cls.stopSupervisorGracefully()
    if hasattr(cls, '_process_manager'):
      cls._process_manager.killPreviousRun()

  @classmethod
  def setUpWorkingDirectory(cls):
    """Initialise the directories"""
    cls.working_directory = os.environ.get(
        'SLAPOS_TEST_WORKING_DIR',
        os.path.join(os.path.dirname(__file__), '.slapos'))
    # To prevent error: Cannot open an HTTP server: socket.error reported
    # AF_UNIX path too long This `working_directory` should not be too deep.
    # Socket path is 108 char max on linux
    # https://github.com/torvalds/linux/blob/3848ec5/net/unix/af_unix.c#L234-L238
    # Supervisord socket name contains the pid number, which is why we add
    # .xxxxxxx in this check.
    if len(cls.working_directory + '/inst/supervisord.socket.xxxxxxx') > 108:
      raise RuntimeError('working directory ( {} ) is too deep, try setting '
              'SLAPOS_TEST_WORKING_DIR'.format(cls.working_directory))

    if not os.path.exists(cls.working_directory):
      os.mkdir(cls.working_directory)

  @classmethod
  def setUpConfig(cls):
    """Create slapos configuration"""
    cls.config = {
      "working_directory": cls.working_directory,
      "slapos_directory": cls.working_directory,
      "log_directory": cls.working_directory,
      "computer_id": 'slapos.test',  # XXX
      'proxy_database': os.path.join(cls.working_directory, 'proxy.db'),
      'partition_reference': cls.__name__,
      # "proper" slapos command must be in $PATH
      'slapos_binary': 'slapos',
      "node_quantity": "3",
    }
    # Some tests are expecting that local IP is not set to 127.0.0.1
    ipv4_address = os.environ.get('SLAPOS_TEST_IPV4', '127.0.1.1')
    ipv6_address = os.environ['SLAPOS_TEST_IPV6']

    cls.config['proxy_host'] = cls.config['ipv4_address'] = ipv4_address
    cls.config['ipv6_address'] = ipv6_address
    cls.config['proxy_port'] = SLAPOS_PROXY_PORT
    cls.config['master_url'] = 'http://{proxy_host}:{proxy_port}'.format(
      **cls.config)

  @classmethod
  def setUpSlapOSController(cls):
    """Create the a "slapos controller" and supply softwares from `getSoftwareURLList`.

    This is equivalent to:

    slapos proxy start
    for sr in getSoftwareURLList; do
      slapos supply $SR $COMP
    done
    """
    cls._process_manager = ProcessManager()

    # XXX this code is copied from testnode code
    cls.slapos_controler = SlapOSControler(
        cls.working_directory,
        cls.config
    )

    slapproxy_log = os.path.join(cls.config['log_directory'], 'slapproxy.log')
    logger = logging.getLogger(__name__)
    logger.debug('Configured slapproxy log to %r', slapproxy_log)

    cls.software_url_list = cls.getSoftwareURLList()
    cls.slapos_controler.initializeSlapOSControler(
        slapproxy_log=slapproxy_log,
        process_manager=cls._process_manager,
        reset_software=False,
        software_path_list=cls.software_url_list)

    # XXX we should check *earlier* if that pidfile exist and if supervisord
    # process still running, because if developer started supervisord (or bugs?)
    # then another supervisord will start and starting services a second time
    # will fail.
    cls._process_manager.supervisord_pid_file = os.path.join(
      cls.slapos_controler.instance_root, 'var', 'run', 'supervisord.pid')

  @classmethod
  def runSoftwareRelease(cls):
    """Run all the software releases that were supplied before.

    This is the equivalent of `slapos node software`.

    The tests will be marked file if software building fail.
    """
    logger = logging.getLogger()
    logger.level = logging.DEBUG
    stream = StringIO.StringIO()
    stream_handler = logging.StreamHandler(stream)
    logger.addHandler(stream_handler)

    try:
      cls.software_status_dict = cls.slapos_controler.runSoftwareRelease(
        cls.config, environment=os.environ)
      stream.seek(0)
      stream.flush()
      message = ''.join(stream.readlines()[-100:])
      assert cls.software_status_dict['status_code'] == 0, message
    finally:
      logger.removeHandler(stream_handler)
      del stream


  @classmethod
  def runComputerPartition(cls, max_quantity=None):
    """Instanciate the software.

    This is the equivalent of doing:

    slapos request --type=getInstanceSoftwareType --parameters=getInstanceParameterDict
    slapos node instance

    and return the slapos request instance parameters.

    This can be called by tests to simulate re-request with different parameters.
    """
    run_cp_kw = {}
    if max_quantity is not None:
      run_cp_kw['max_quantity'] = max_quantity
    logger = logging.getLogger()
    logger.level = logging.DEBUG
    stream = StringIO.StringIO()
    stream_handler = logging.StreamHandler(stream)
    logger.addHandler(stream_handler)

    if cls.getInstanceSoftwareType() != 'default':
      raise NotImplementedError

    instance_parameter_dict = cls.getInstanceParameterDict()
    try:
      cls.instance_status_dict = cls.slapos_controler.runComputerPartition(
        cls.config,
        cluster_configuration=instance_parameter_dict,
        environment=os.environ,
        **run_cp_kw)
      stream.seek(0)
      stream.flush()
      message = ''.join(stream.readlines()[-100:])
      assert cls.instance_status_dict['status_code'] == 0, message
    finally:
      logger.removeHandler(stream_handler)
      del stream

    # FIXME: similar to test node, only one (root) partition is really
    #        supported for now.
    computer_partition_list = []
    for i in range(len(cls.software_url_list)):
      computer_partition_list.append(
          cls.slapos_controler.slap.registerOpenOrder().request(
            cls.software_url_list[i],
            # This is how testnode's SlapOSControler name created partitions
            partition_reference='testing partition {i}'.format(
              i=i, **cls.config),
            partition_parameter_kw=instance_parameter_dict))

    # expose some class attributes so that tests can use them:
    # the ComputerPartition instances, to getInstanceParameterDict
    cls.computer_partition = computer_partition_list[0]

    # the path of the instance on the filesystem, for low level inspection
    cls.computer_partition_root_path = os.path.join(
        cls.config['working_directory'],
        'inst',
        cls.computer_partition.getId())



