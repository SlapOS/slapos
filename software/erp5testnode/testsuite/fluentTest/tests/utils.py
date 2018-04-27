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

from erp5.util.testnode.SlapOSControler import SlapOSControler
from erp5.util.testnode.ProcessManager import ProcessManager
import slapos


def findFreeTCPPort(ip=''):
  """Find a free TCP port to listen to.
  """
  family = socket.AF_INET6 if ':' in ip else socket.AF_INET
  with closing(socket.socket(family, socket.SOCK_STREAM)) as s:
    s.bind((ip, 0))
    return s.getsockname()[1]


class SlapOSInstanceTestCase(unittest.TestCase):
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

 # TODO: allow subclasses to request a specific software type ?
  
  @classmethod
  def setUpClass(cls):
    try:
      cls._setUpClass()
    except:
      cls.tearDownClass()
      raise

  @classmethod
  def _setUpClass(cls):

    working_directory = os.environ.get(
        'SLAPOS_TEST_WORKING_DIR',
        os.path.join(os.path.dirname(__file__), '.slapos'))
    # To prevent error: Cannot open an HTTP server: socket.error reported
    # AF_UNIX path too long This `working_directory` should not be too deep.
    # Socket path is 108 char max on linux
    # https://github.com/torvalds/linux/blob/3848ec5/net/unix/af_unix.c#L234-L238
    if len(working_directory + '/inst/supervisord.socket.xxxxxxx') > 108:
       raise RuntimeError('working directory ( {} ) is too deep, try setting '
               'SLAPOS_TEST_WORKING_DIR'.format(working_directory))
    if not os.path.exists(working_directory):
      os.mkdir(working_directory)

    cls.config = config = {
      "working_directory": working_directory,
      "slapos_directory": working_directory,
      "log_directory": working_directory,
      "computer_id": 'slapos.test', # XXX
      'proxy_database': os.path.join(working_directory, 'proxy.db'),
      'partition_reference': cls.__name__,
      # "proper" slapos command must be in $PATH
      'slapos_binary': 'slapos',
    }

    # Some tests are expecting that local IP is not set to 127.0.0.1
    ipv4_address = os.environ.get('LOCAL_IPV4', '127.0.1.1')
    ipv6_address = os.environ['GLOBAL_IPV6']
    
    config['proxy_host'] = config['ipv4_address'] = ipv4_address
    config['ipv6_address'] = ipv6_address
    config['proxy_port'] = findFreeTCPPort(ipv4_address)
    config['master_url'] = 'http://{proxy_host}:{proxy_port}'.format(**config)

    cls._process_manager = process_manager = ProcessManager()

    # XXX this code is copied from testnode code
    slapos_controler = SlapOSControler(
        working_directory,
        config
    )

    slapproxy_log = os.path.join(config['log_directory'], 'slapproxy.log')
    logger = logging.getLogger(__name__)
    logger.debug('Configured slapproxy log to %r', slapproxy_log)

    software_url_list = cls.getSoftwareURLList()
    slapos_controler.initializeSlapOSControler(
        slapproxy_log=slapproxy_log,
        process_manager=process_manager,
        reset_software=False,
        software_path_list=software_url_list)

    process_manager.supervisord_pid_file = os.path.join(
           slapos_controler.instance_root, 'var', 'run', 'supervisord.pid')

    software_status_dict = slapos_controler.runSoftwareRelease(config, environment=os.environ)
    # TODO: log more details in this case
    assert software_status_dict['status_code'] == 0

    instance_parameter_dict = cls.getInstanceParameterDict()
    instance_status_dict = slapos_controler.runComputerPartition(
        config,
        cluster_configuration=instance_parameter_dict,
        environment=os.environ)
    # TODO: log more details in this case
    assert instance_status_dict['status_code'] == 0

    # FIXME: similar to test node, only one (root) partition is really supported for now.
    computer_partition_list = []
    for i in range(len(software_url_list)):
      computer_partition_list.append(
          slapos_controler.slap.registerOpenOrder().request(
          software_url_list[i],
          # This is how testnode's SlapOSControler name created partitions
          partition_reference='testing partition {i}'.format(i=i, **config),
          partition_parameter_kw=instance_parameter_dict))

    # expose some class attributes so that tests can use them:
    # the ComputerPartition instances, to getInstanceParmeterDict
    cls.computer_partition = computer_partition_list[0]

    # the path of the instance on the filesystem, for low level inspection
    cls.computer_partition_root_path = os.path.join(
        config['working_directory'],
        'inst',
        cls.computer_partition.getId())
  

  @classmethod
  def tearDownClass(cls):
    if hasattr(cls, '_process_manager'):
      cls._process_manager.killPreviousRun()
