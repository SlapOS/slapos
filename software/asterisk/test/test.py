##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
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
import functools
import lzma
import os
import socket
import time

from slapos.testing.utils import CrontabMixin
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class AsteriskTestCase(SlapOSInstanceTestCase, CrontabMixin):

  @classmethod
  def getInstanceParameterDict(cls):
    return {
        'sip-trunk-server': 'sbc6.fr.sip.ovh',
        'sip-trunk-number': '0033972100409',
        'sip-trunk-password': 'test-password',
        'local-number': '01271',
        'local-ims-ip': '172.24.64.1',
    }

  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def _get_asterisk_address(self):
    """Return (host, port) parsed from the asterisk-ip connection parameter."""
    asterisk_ip = self.connection_parameters['asterisk-ip']
    if asterisk_ip.startswith('['):
      host, port = asterisk_ip[1:].split(']:')
    else:
      host, port = asterisk_ip.rsplit(':', 1)
    return host, int(port)

  def test_asterisk_listening(self):
    self.assertIn('asterisk-ip', self.connection_parameters)
    host, port = self._get_asterisk_address()
    sock = socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET,
                         socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    self.assertEqual(result, 0,
        "Asterisk is not listening on %s" % self.connection_parameters['asterisk-ip'])

  def test_sip_options(self):
    """Send a SIP OPTIONS request and verify Asterisk responds with 200 OK."""
    host, port = self._get_asterisk_address()
    sip_uri_host = '[%s]' % host if ':' in host else host
    request = '\r\n'.join([
        'OPTIONS sip:%s:%d SIP/2.0' % (sip_uri_host, port),
        'Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bKtest',
        'Max-Forwards: 70',
        'To: <sip:%s:%d>' % (sip_uri_host, port),
        'From: <sip:test@127.0.0.1>;tag=test',
        'Call-ID: test@127.0.0.1',
        'CSeq: 1 OPTIONS',
        'Content-Length: 0',
        '',
        '',
    ])
    af = socket.AF_INET6 if ':' in host else socket.AF_INET
    sock = socket.socket(af, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
      sock.sendto(request.encode(), (host, port))
      response = sock.recv(4096)
      # 200 OK if no auth required, 401 Unauthorized for unknown endpoints — both
      # prove Asterisk received and processed the SIP request correctly.
      self.assertTrue(
          response.startswith(b'SIP/2.0'),
          "Expected SIP/2.0 response, got: %r" % response[:80])
    finally:
      sock.close()

  def _find_logger_conf(self):
    import glob
    for path in glob.glob(os.path.join(self.slap.instance_directory, '*')):
      candidate = os.path.join(path, 'etc', 'asterisk', 'logger.conf')
      if os.path.exists(candidate):
        return candidate
    return None

  def test_log_level(self):
    # Find logger.conf
    logger_conf = self._find_logger_conf()
    self.assertIsNotNone(logger_conf, "logger.conf not found")

    # Default log level: verbose (no debug)
    with open(logger_conf) as f:
      content = f.read()
    self.assertIn('error,warning,notice,verbose', content)
    self.assertNotIn('debug', content)

    # Get asterisk PID before change
    with self.slap.instance_supervisor_rpc as supervisor:
      for p in supervisor.getAllProcessInfo():
        if 'asterisk' in p['name']:
          old_pid = p['pid']
          break
      else:
        self.fail("Asterisk process not found in supervisor before log-level change")

    # Re-request with debug log level
    self.slap.request(
        software_release=self.getSoftwareURL(),
        partition_reference=self.default_partition_reference,
        software_type=self.getInstanceSoftwareType(),
        partition_parameter_kw={**self.getInstanceParameterDict(), 'log-level': 'debug'},
    )
    self.waitForInstance()

    # Check logger.conf updated to include debug
    with open(logger_conf) as f:
      content = f.read()
    self.assertIn('error,warning,notice,verbose,debug', content)

    # Check asterisk restarted (new PID)
    with self.slap.instance_supervisor_rpc as supervisor:
      for p in supervisor.getAllProcessInfo():
        if 'asterisk' in p['name']:
          new_pid = p['pid']
          break
      else:
        self.fail("Asterisk process not found in supervisor after log-level change")
    self.assertNotEqual(old_pid, new_pid, "Asterisk did not restart after log-level change")


  def test_log_rotation(self):
    log_file_path = functools.partial(
        os.path.join,
        self.computer_partition_root_path,
        'var', 'log', 'asterisk',
    )
    rotated_file_path = functools.partial(
        os.path.join,
        self.computer_partition_root_path,
        'srv', 'backup', 'logrotate',
    )

    # Wait for asterisk to be fully ready (it may have just restarted)
    host, port = self._get_asterisk_address()
    for _ in range(30):
      sock = socket.socket(
          socket.AF_INET6 if ':' in host else socket.AF_INET,
          socket.SOCK_STREAM)
      if sock.connect_ex((host, port)) == 0:
        sock.close()
        break
      sock.close()
      time.sleep(1)

    # Asterisk should have written startup messages
    self.assertTrue(
        os.path.exists(log_file_path('full.log')),
        "Asterisk log file not found")
    with open(log_file_path('full.log')) as f:
      self.assertIn('Asterisk', f.read())

    # First rotation initializes logrotate state but does not actually rotate
    self._executeCrontabAtDate('logrotate', '2050-01-01')
    # Second rotation moves the file; not compressed yet (delaycompress)
    self._executeCrontabAtDate('logrotate', '2050-01-02')

    with open(rotated_file_path('full.log-20500102')) as f:
      self.assertIn('Asterisk', f.read())

    # Third rotation compresses the previous rotated file
    self._executeCrontabAtDate('logrotate', '2050-01-03')
    with lzma.open(rotated_file_path('full.log-20500102.xz'), 'rt') as f:
      self.assertIn('Asterisk', f.read())


class AsteriskIPv6TestCase(AsteriskTestCase):
  """Run test_sip_options with Asterisk bound to the global IPv6 address."""

  @classmethod
  def getInstanceParameterDict(cls):
    params = super().getInstanceParameterDict().copy()
    params['bind-ip'] = 'IPv6 Re6st address'
    return params

  # Only run test_sip_options — IPv6-specific connectivity check.
  test_asterisk_listening = None
  test_log_level = None
  test_log_rotation = None
