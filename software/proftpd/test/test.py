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

import os
import shutil
import urlparse
import tempfile
import StringIO
import subprocess

import pysftp
from paramiko.ssh_exception import SSHException
from paramiko.ssh_exception import AuthenticationException

import utils


# for development: debugging logs and install Ctrl+C handler
if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


class ProFTPdTestCase(utils.SlapOSInstanceTestCase):
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')), )

  def _getConnection(self, username=None, password=None, hostname=None):
    """Returns a pysftp connection connected to the SFTP

    username and password can be specified and default to the ones from
    instance connection parameters.
    another hostname can also be passed.
    """
    # this tells paramiko not to verify host key
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    parameter_dict = self.computer_partition.getConnectionParameterDict()
    sftp_url = urlparse.urlparse(parameter_dict['url'])

    return pysftp.Connection(
        hostname or sftp_url.hostname,
        port=sftp_url.port,
        cnopts=cnopts,
        username=username or parameter_dict['username'],
        password=password or parameter_dict['password'])


class TestSFTPListen(ProFTPdTestCase):
  def test_listen_on_ipv4(self):
    self.assertTrue(self._getConnection(hostname=self.config['ipv4_address']))

  def test_does_not_listen_on_all_ip(self):
    with self.assertRaises(SSHException):
      self._getConnection(hostname='0.0.0.0')


class TestSFTPOperations(ProFTPdTestCase):
  """Tests upload / download features we expect in SFTP server.
  """
  def setUp(self):
    self.upload_dir = os.path.join(
        self.computer_partition_root_path, 'srv', 'proftpd')

  def tearDown(self):
    for name in os.listdir(self.upload_dir):
      path = os.path.join(self.upload_dir, name)
      if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
      else:
        shutil.rmtree(path)

  def test_simple_sftp_session(self):
    with self._getConnection() as sftp:
      # put a file
      with tempfile.NamedTemporaryFile() as f:
        f.write("Hello FTP !")
        f.flush()
        sftp.put(f.name, remotepath='testfile')

      # it's visible in listdir()
      self.assertEqual(['testfile'], sftp.listdir())

      # and also in the server filesystem
      self.assertEqual(['testfile'], os.listdir(self.upload_dir))

      # download the file again, it should have same content
      tempdir = tempfile.mkdtemp()
      self.addCleanup(lambda : shutil.rmtree(tempdir))
      local_file = os.path.join(tempdir, 'testfile')
      retrieve_same_file = sftp.get('testfile', local_file)
      with open(local_file) as f:
        self.assertEqual(f.read(), "Hello FTP !")

  def test_uploaded_file_not_visible_until_fully_uploaded(self):
    test_self = self
    class PartialFile(StringIO.StringIO):
      def read(self, *args):
        # file is not visible yet
        test_self.assertNotIn('destination', os.listdir(test_self.upload_dir))
        # it's just a hidden file
        test_self.assertEqual(['.in.destination.'], os.listdir(test_self.upload_dir))
        return StringIO.StringIO.read(self, *args)

    with self._getConnection() as sftp:
      sftp.sftp_client.putfo(PartialFile("content"), "destination")

    # now file is visible
    self.assertEqual(['destination'], os.listdir(self.upload_dir))

  def test_partial_upload_are_deleted(self):
    test_self = self
    with self._getConnection() as sftp:
      class ErrorFile(StringIO.StringIO):
        def read(self, *args):
          # at this point, file is already created on server
          test_self.assertEqual(['.in.destination.'], os.listdir(test_self.upload_dir))
          # simulate a connection closed
          sftp.sftp_client.close()
          return "something that will not be sent to server"
      with self.assertRaises(IOError):
        sftp.sftp_client.putfo(ErrorFile(), "destination")
    # no half uploaded file is kept
    self.assertEqual([], os.listdir(self.upload_dir))

  def test_user_cannot_escape_home(self):
    with self._getConnection() as sftp:
      with self.assertRaisesRegexp(IOError, 'Permission denied'):
        sftp.listdir('..')
      with self.assertRaisesRegexp(IOError, 'Permission denied'):
        sftp.listdir('/')
      with self.assertRaisesRegexp(IOError, 'Permission denied'):
        sftp.listdir('/tmp/')


class TestUserManagement(ProFTPdTestCase):
  def test_user_can_be_added_from_script(self):
    with self.assertRaisesRegexp(AuthenticationException, 'Authentication failed'):
      self._getConnection(username='bob', password='secret')

    subprocess.check_call(
      'echo secret | %s/bin/ftpasswd --name=bob --stdin' % self.computer_partition_root_path,
      shell=True)
    self.assertTrue(self._getConnection(username='bob', password='secret'))


class TestBan(ProFTPdTestCase):
  def test_client_are_banned_after_5_wrong_passwords(self):
    # Simulate failed 5 login attempts
    for i in range(5):
      with self.assertRaisesRegexp(AuthenticationException, 'Authentication failed'):
        self._getConnection(password='wrong')

    # after that, even with a valid password we cannot connect
    with self.assertRaisesRegexp(SSHException, 'Connection reset by peer'):
      self._getConnection()

    # ban event is logged
    with open(os.path.join(
        self.computer_partition_root_path, 'var', 'log', 'proftpd-ban.log')) as ban_log_file:
      self.assertRegexpMatches(
        ban_log_file.readlines()[-1],
        'login from host .* denied due to host ban')


class TestInstanceParameterPort(ProFTPdTestCase):
  @classmethod
  def getInstanceParmeterDict(cls):
    cls.free_port = utils.findFreeTCPPort(cls.config['ipv4_address'])
    return {'port': cls.free_port}

  def test_instance_parameter_port(self):
    parameter_dict = self.computer_partition.getConnectionParameterDict()
    sftp_url = urlparse.urlparse(parameter_dict['url'])
    self.assertEqual(self.free_port, sftp_url.port)
    self.assertTrue(self._getConnection())


