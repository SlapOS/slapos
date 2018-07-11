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
import subprocess
from contextlib import closing
import logging
import StringIO
import json
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import xmlrpclib
import supervisor.xmlrpc

from erp5.util.testnode.SlapOSControler import SlapOSControler
from erp5.util.testnode.ProcessManager import ProcessManager


LOCAL_IPV4 = os.environ['LOCAL_IPV4']
GLOBAL_IPV6 = os.environ['GLOBAL_IPV6']


def der2pem(der):
  certificate, error = subprocess.Popen(
      'openssl x509 -inform der'.split(), stdin=subprocess.PIPE,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE
  ).communicate(der)
  if error:
    raise ValueError(error)
  return certificate


def findFreeTCPPort(ip=''):
  """Find a free TCP port to listen to.
  """
  family = socket.AF_INET6 if ':' in ip else socket.AF_INET
  with closing(socket.socket(family, socket.SOCK_STREAM)) as s:
    s.bind((ip, 0))
    return s.getsockname()[1]


class SlapOSInstanceTestCase(unittest.TestCase):
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
           serverurl="unix://{working_directory}/inst/supervisord.socket"
           .format(**self.config)))

  @classmethod
  def getSoftwareURLList(cls):
    """Return URL of software releases to install.

    To be defined by subclasses.
    """
    return [os.path.realpath(os.environ['TEST_SR'])]

  @classmethod
  def getInstanceParameterDict(cls):
    """Return instance parameters

    To be defined by subclasses if they need to request instance with specific
    parameters.
    """
    return {}

 # TODO: allow subclasses to request a specific software type ?

  @classmethod
  def setUpWorkingDirectory(cls):
    cls.working_directory = os.environ.get(
        'SLAPOS_TEST_WORKING_DIR',
        os.path.join(os.path.dirname(__file__), '.slapos'))
    # To prevent error: Cannot open an HTTP server: socket.error reported
    # AF_UNIX path too long This `working_directory` should not be too deep.
    # Socket path is 108 char max on linux
    # https://github.com/torvalds/linux/blob/3848ec5/net/unix/af_unix.c#L234-L238
    if len(cls.working_directory + '/inst/supervisord.socket.xxxxxxx') > 108:
      raise RuntimeError(
        'working directory ( {} ) is too deep, try setting '
        'SLAPOS_TEST_WORKING_DIR'.format(cls.working_directory))

    if not os.path.exists(cls.working_directory):
      os.mkdir(cls.working_directory)

  @classmethod
  def setUpConfig(cls):
    cls.config = {
      "working_directory": cls.working_directory,
      "slapos_directory": cls.working_directory,
      "log_directory": cls.working_directory,
      "computer_id": 'slapos.test',  # XXX
      'proxy_database': os.path.join(cls.working_directory, 'proxy.db'),
      'partition_reference': cls.__name__,
      # "proper" slapos command must be in $PATH
      'slapos_binary': 'slapos',
    }
    ipv4_address = LOCAL_IPV4
    ipv6_address = os.environ['GLOBAL_IPV6']

    cls.config['proxy_host'] = cls.config['ipv4_address'] = ipv4_address
    cls.config['ipv6_address'] = ipv6_address
    cls.config['proxy_port'] = findFreeTCPPort(ipv4_address)
    cls.config['master_url'] = 'http://{proxy_host}:{proxy_port}'.format(
      **cls.config)

  @classmethod
  def setUpSlapOSController(cls):
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

    cls._process_manager.supervisord_pid_file = os.path.join(
      cls.slapos_controler.instance_root, 'var', 'run', 'supervisord.pid')

  @classmethod
  def runSoftwareRelease(cls):

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
  def runComputerPartition(cls):
    logger = logging.getLogger()
    logger.level = logging.DEBUG
    stream = StringIO.StringIO()
    stream_handler = logging.StreamHandler(stream)
    logger.addHandler(stream_handler)

    instance_parameter_dict = cls.getInstanceParameterDict()
    try:
      cls.instance_status_dict = cls.slapos_controler.runComputerPartition(
        cls.config,
        cluster_configuration=instance_parameter_dict,
        environment=os.environ)
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

    # expose instance directory
    cls.instance_path = os.path.join(
        cls.config['working_directory'],
        'inst')
    # the path of the instance on the filesystem, for low level inspection
    cls.computer_partition_root_path = os.path.join(
        cls.instance_path,
        cls.computer_partition.getId())
    # expose software directory, extract from found computer partition
    cls.software_path = os.path.realpath(os.path.join(
      cls.computer_partition_root_path, 'software_release'))

  @classmethod
  def setUpClass(cls):
    try:
      cls.setUpWorkingDirectory()
      cls.setUpConfig()
      cls.setUpSlapOSController()
      cls.runSoftwareRelease()
      cls.runComputerPartition()
    except Exception:
      cls.tearDownClass()
      raise

  @classmethod
  def tearDownClass(cls):
    if getattr(cls, '_process_manager', None) is not None:
      cls._process_manager.killPreviousRun()


class TestHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/json")
    self.send_header('Set-Cookie', 'secured=value;secure')
    self.send_header('Set-Cookie', 'nonsecured=value')
    self.end_headers()
    response = {
      'Path': self.path,
      'Incoming Headers': self.headers.dict
    }
    self.wfile.write(json.dumps(response, indent=2))


if __name__ == '__main__':
  ip = LOCAL_IPV4
  port = 8888
  server = HTTPServer((ip, port), TestHandler)
  print 'http://%s:%s' % server.server_address
  server.serve_forever()
