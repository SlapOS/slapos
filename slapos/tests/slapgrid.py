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

import httplib
import logging
import os
import random
import shutil
import signal
import socket
import sys
import tempfile
import textwrap
import time
import unittest
import urlparse

import xml_marshaller

import slapos.slap.slap
import slapos.grid.utils
from slapos.grid import slapgrid
from slapos.cli_legacy.slapgrid import parseArgumentTupleAndReturnSlapgridObject
from slapos.grid.utils import md5digest
from slapos.grid.watchdog import Watchdog, getWatchdogID
from slapos.grid import SlapObject

dummylogger = logging.getLogger()


WATCHDOG_TEMPLATE = """#!{python_path} -S
import sys
sys.path={sys_path}
import slapos.slap
import slapos.grid.watchdog

def bang(self_partition, message):
  nl = chr(10)
  with open('{watchdog_banged}', 'w') as fout:
    for key, value in vars(self_partition).items():
      fout.write('%s: %s%s' % (key, value, nl))
      if key == '_connection_helper':
        for k, v in vars(value).items():
          fout.write('   %s: %s%s' % (k, v, nl))
    fout.write(message)

slapos.slap.ComputerPartition.bang = bang
slapos.grid.watchdog.main()
"""

WRAPPER_CONTENT = """#!/bin/sh
touch worked &&
mkdir -p etc/run &&
echo "#!/bin/sh" > etc/run/wrapper &&
echo "while true; do echo Working; sleep 0.1; done" >> etc/run/wrapper &&
chmod 755 etc/run/wrapper
"""

DAEMON_CONTENT = """#!/bin/sh
mkdir -p etc/service &&
echo "#!/bin/sh" > etc/service/daemon &&
echo "touch launched
if [ -f ./crashed ]; then
while true; do echo Working; sleep 0.1; done
else
touch ./crashed; echo Failing; sleep 1; exit 111;
fi" >> etc/service/daemon &&
chmod 755 etc/service/daemon &&
touch worked
"""


class BasicMixin:
  def setUp(self):
    self._tempdir = tempfile.mkdtemp()
    self.software_root = os.path.join(self._tempdir, 'software')
    self.instance_root = os.path.join(self._tempdir, 'instance')
    logging.basicConfig(level=logging.DEBUG)
    self.setSlapgrid()

  def setSlapgrid(self, develop=False):
    if getattr(self, 'master_url', None) is None:
      self.master_url = 'http://127.0.0.1:80/'
    self.computer_id = 'computer'
    self.supervisord_socket = os.path.join(self._tempdir, 'supervisord.sock')
    self.supervisord_configuration_path = os.path.join(self._tempdir,
                                                       'supervisord')
    self.usage_report_periodicity = 1
    self.buildout = None
    self.grid = slapgrid.Slapgrid(self.software_root,
                                  self.instance_root,
                                  self.master_url,
                                  self.computer_id,
                                  self.supervisord_socket,
                                  self.supervisord_configuration_path,
                                  self.buildout,
                                  develop=develop,
                                  logger=logging.getLogger())
    # monkey patch buildout bootstrap

    def dummy(*args, **kw):
      pass

    slapos.grid.utils.bootstrapBuildout = dummy

    SlapObject.PROGRAM_PARTITION_TEMPLATE = textwrap.dedent("""\
        [program:%(program_id)s]
        directory=%(program_directory)s
        command=%(program_command)s
        process_name=%(program_name)s
        autostart=false
        autorestart=false
        startsecs=0
        startretries=0
        exitcodes=0
        stopsignal=TERM
        stopwaitsecs=60
        stopasgroup=true
        killasgroup=true
        user=%(user_id)s
        group=%(group_id)s
        serverurl=AUTO
        redirect_stderr=true
        stdout_logfile=%(instance_path)s/.%(program_id)s.log
        stderr_logfile=%(instance_path)s/.%(program_id)s.log
        environment=USER="%(USER)s",LOGNAME="%(USER)s",HOME="%(HOME)s"
        """)

  def launchSlapgrid(self, develop=False):
    self.setSlapgrid(develop=develop)
    return self.grid.processComputerPartitionList()

  def launchSlapgridSoftware(self, develop=False):
    self.setSlapgrid(develop=develop)
    return self.grid.processSoftwareReleaseList()

  def assertLogContent(self, log_path, expected, tries=50):
    for i in range(tries):
      if expected in open(log_path).read():
        return
      time.sleep(0.1)
    self.fail('%r not found in %s' % (expected, log_path))

  def assertIsCreated(self, path, tries=50):
    for i in range(tries):
      if os.path.exists(path):
        return
      time.sleep(0.1)
    self.fail('%s should be created' % path)

  def assertIsNotCreated(self, path, tries=50):
    for i in range(tries):
      if os.path.exists(path):
        self.fail('%s should not be created' % path)
      time.sleep(0.1)

  def tearDown(self):
    # XXX: Hardcoded pid, as it is not configurable in slapos
    svc = os.path.join(self.instance_root, 'var', 'run', 'supervisord.pid')
    if os.path.exists(svc):
      try:
        pid = int(open(svc).read().strip())
      except ValueError:
        pass
      else:
        os.kill(pid, signal.SIGTERM)
    shutil.rmtree(self._tempdir, True)


class TestRequiredOnlyPartitions(unittest.TestCase):
  def test_no_errors(self):
    required = ['one', 'three']
    existing = ['one', 'two', 'three']
    slapgrid.check_required_only_partitions(existing, required)

  def test_one_missing(self):
    required = ['foobar', 'two', 'one']
    existing = ['one', 'two', 'three']
    self.assertRaisesRegexp(ValueError,
                            'Unknown partition: foobar',
                            slapgrid.check_required_only_partitions,
                            existing, required)

  def test_several_missing(self):
    required = ['foobar', 'barbaz']
    existing = ['one', 'two', 'three']
    self.assertRaisesRegexp(ValueError,
                            'Unknown partitions: barbaz, foobar',
                            slapgrid.check_required_only_partitions,
                            existing, required)


class TestBasicSlapgridCP(BasicMixin, unittest.TestCase):
  def test_no_software_root(self):
    self.assertRaises(OSError, self.grid.processComputerPartitionList)

  def test_no_instance_root(self):
    os.mkdir(self.software_root)
    self.assertRaises(OSError, self.grid.processComputerPartitionList)

  def test_no_master(self):
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    self.assertRaises(socket.error, self.grid.processComputerPartitionList)


class MasterMixin(BasicMixin):

  def _patchHttplib(self):
    """Overrides httplib"""
    import mock.httplib

    self.saved_httplib = {}

    for fake in vars(mock.httplib):
      self.saved_httplib[fake] = getattr(httplib, fake, None)
      setattr(httplib, fake, getattr(mock.httplib, fake))

  def _unpatchHttplib(self):
    """Restores httplib overriding"""
    import httplib
    for name, original_value in self.saved_httplib.items():
      setattr(httplib, name, original_value)
    del self.saved_httplib

  def _mock_sleep(self):
    self.fake_waiting_time = None
    self.real_sleep = time.sleep

    def mocked_sleep(secs):
      if self.fake_waiting_time is not None:
        secs = self.fake_waiting_time
      self.real_sleep(secs)

    time.sleep = mocked_sleep

  def _unmock_sleep(self):
    time.sleep = self.real_sleep

  def setUp(self):
    self._patchHttplib()
    self._mock_sleep()
    BasicMixin.setUp(self)

  def tearDown(self):
    self._unpatchHttplib()
    self._unmock_sleep()
    BasicMixin.tearDown(self)


class ComputerForTest:
  """
  Class to set up environment for tests setting instance, software
  and server response
  """
  def __init__(self,
               software_root,
               instance_root,
               instance_amount=1,
               software_amount=1):
    """
    Will set up instances, software and sequence
    """
    self.sequence = []
    self.instance_amount = instance_amount
    self.software_amount = software_amount
    self.software_root = software_root
    self.instance_root = instance_root
    if not os.path.isdir(self.instance_root):
      os.mkdir(self.instance_root)
    if not os.path.isdir(self.software_root):
      os.mkdir(self.software_root)
    self.setSoftwares()
    self.setInstances()
    self.setServerResponse()

  def setSoftwares(self):
    """
    Will set requested amount of software
    """
    self.software_list = [
        SoftwareForTest(self.software_root, name=str(i))
        for i in range(self.software_amount)
    ]

  def setInstances(self):
    """
    Will set requested amount of instance giving them by default first software
    """
    if self.software_list:
      software = self.software_list[0]
    else:
      software = None

    self.instance_list = [
        InstanceForTest(self.instance_root, name=str(i), software=software)
        for i in range(self.instance_amount)
    ]

  def getComputer(self, computer_id):
    """
    Will return current requested state of computer
    """
    slap_computer = slapos.slap.Computer(computer_id)
    slap_computer._software_release_list = [
        software.getSoftware(computer_id)
        for software in self.software_list
    ]
    slap_computer._computer_partition_list = [
        instance.getInstance(computer_id)
        for instance in self.instance_list
    ]
    return slap_computer

  def setServerResponse(self):
    httplib.HTTPConnection._callback = self.getServerResponse()
    httplib.HTTPSConnection._callback = self.getServerResponse()

  def getServerResponse(self):
    """
    Define _callback.
    Will register global sequence of message, sequence by partition
    and error and error message by partition
    """
    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      self.sequence.append(parsed_url.path)
      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)
      if (parsed_url.path == 'getFullComputerInformation'
              and 'computer_id' in parsed_qs):
        slap_computer = self.getComputer(parsed_qs['computer_id'][0])
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if method == 'POST' and 'computer_partition_id' in parsed_qs:
        instance = self.instance_list[int(parsed_qs['computer_partition_id'][0])]
        instance.sequence.append(parsed_url.path)
        instance.header_list.append(header)
        if parsed_url.path == 'availableComputerPartition':
          return (200, {}, '')
        if parsed_url.path == 'startedComputerPartition':
          instance.state = 'started'
          return (200, {}, '')
        if parsed_url.path == 'stoppedComputerPartition':
          instance.state = 'stopped'
          return (200, {}, '')
        if parsed_url.path == 'destroyedComputerPartition':
          instance.state = 'destroyed'
          return (200, {}, '')
        if parsed_url.path == 'softwareInstanceBang':
          return (200, {}, '')
        if parsed_url.path == 'softwareInstanceError':
          instance.error_log = '\n'.join(
              [
                  line
                  for line in parsed_qs['error_log'][0].splitlines()
                  if 'dropPrivileges' not in line
              ]
          )
          instance.error = True
          return (200, {}, '')

      elif method == 'POST' and 'url' in parsed_qs:
        # XXX hardcoded to first software release!
        software = self.software_list[0]
        software.sequence.append(parsed_url.path)
        if parsed_url.path == 'buildingSoftwareRelease':
          return (200, {}, '')
        if parsed_url.path == 'softwareReleaseError':
          software.error_log = '\n'.join(
              [
                  line
                  for line in parsed_qs['error_log'][0].splitlines()
                  if 'dropPrivileges' not in line
              ]
          )
          software.error = True
          return (200, {}, '')

      else:
        return (500, {}, '')
    return server_response


class InstanceForTest:
  """
  Class containing all needed paramaters and function to simulate instances
  """
  def __init__(self, instance_root, name, software):
    self.instance_root = instance_root
    self.software = software
    self.requested_state = 'stopped'
    self.state = None
    self.error = False
    self.error_log = None
    self.sequence = []
    self.header_list = []
    self.name = name
    self.partition_path = os.path.join(self.instance_root, self.name)
    os.mkdir(self.partition_path, 0o750)
    self.timestamp = None

  def getInstance(self, computer_id):
    """
    Will return current requested state of instance
    """
    partition = slapos.slap.ComputerPartition(computer_id, self.name)
    partition._software_release_document = self.getSoftwareRelease()
    partition._requested_state = self.requested_state
    if self.software is not None:
      if self.timestamp is not None:
        partition._parameter_dict = {'timestamp': self.timestamp}
    return partition

  def getSoftwareRelease(self):
    """
    Return software release for Instance
    """
    if self.software is not None:
      sr = slapos.slap.SoftwareRelease()
      sr._software_release = self.software.name
      return sr
    else:
      return None

  def setPromise(self, promise_name, promise_content):
    """
    This function will set promise and return its path
    """
    promise_path = os.path.join(self.partition_path, 'etc', 'promise')
    if not os.path.isdir(promise_path):
      os.makedirs(promise_path)
    promise = os.path.join(promise_path, promise_name)
    open(promise, 'w').write(promise_content)
    os.chmod(promise, 0o777)

  def setCertificate(self, certificate_repository_path):
    if not os.path.exists(certificate_repository_path):
      os.mkdir(certificate_repository_path)
    self.cert_file = os.path.join(certificate_repository_path,
                                  "%s.crt" % self.name)
    self.certificate = str(random.random())
    open(self.cert_file, 'w').write(self.certificate)
    self.key_file = os.path.join(certificate_repository_path,
                                 '%s.key' % self.name)
    self.key = str(random.random())
    open(self.key_file, 'w').write(self.key)


class SoftwareForTest:
  """
  Class to prepare and simulate software.
  each instance has a sotfware attributed
  """
  def __init__(self, software_root, name=''):
    """
    Will set file and variable for software
    """
    self.software_root = software_root
    self.name = 'http://sr%s/' % name
    self.sequence = []
    self.software_hash = md5digest(self.name)
    self.srdir = os.path.join(self.software_root, self.software_hash)
    self.requested_state = 'available'
    os.mkdir(self.srdir)
    self.setTemplateCfg()
    self.srbindir = os.path.join(self.srdir, 'bin')
    os.mkdir(self.srbindir)
    self.setBuildout()

  def getSoftware(self, computer_id):
    """
    Will return current requested state of software
    """
    software = slapos.slap.SoftwareRelease(self.name, computer_id)
    software._requested_state = self.requested_state
    return software

  def setTemplateCfg(self, template="""[buildout]"""):
    """
    Set template.cfg
    """
    open(os.path.join(self.srdir, 'template.cfg'), 'w').write(template)

  def setBuildout(self, buildout="""#!/bin/sh
touch worked"""):
    """
    Set a buildout exec in bin
    """
    open(os.path.join(self.srbindir, 'buildout'), 'w').write(buildout)
    os.chmod(os.path.join(self.srbindir, 'buildout'), 0o755)

  def setPeriodicity(self, periodicity):
    """
    Set a periodicity file
    """
    with open(os.path.join(self.srdir, 'periodicity'), 'w') as fout:
      fout.write(str(periodicity))


class TestSlapgridCPWithMaster(MasterMixin, unittest.TestCase):

  def test_nothing_to_do(self):

    ComputerForTest(self.software_root, self.instance_root, 0, 0)

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['etc', 'var'])
    self.assertItemsEqual(os.listdir(self.software_root), [])

  def test_one_partition(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition), ['buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])

  def test_one_partition_instance_cfg(self):
    """
    Check that slapgrid processes instance is profile is not named
    "template.cfg" but "instance.cfg".
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition), ['buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])

  def test_one_free_partition(self):
    """
    Test if slapgrid cp don't process "free" partition
    """
    computer = ComputerForTest(self.software_root,
                               self.instance_root,
                               software_amount=0)
    partition = computer.instance_list[0]
    partition.requested_state = 'destroyed'
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(partition.partition_path), [])
    self.assertItemsEqual(os.listdir(self.software_root), [])
    self.assertEqual(partition.sequence, [])

  def test_one_partition_started(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    partition = computer.instance_list[0]
    partition.requested_state = 'started'
    partition.software.setBuildout(WRAPPER_CONTENT)
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(partition.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(partition.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertItemsEqual(os.listdir(self.software_root), [partition.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(partition.state, 'started')

  def test_one_partition_started_stopped(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]

    instance.requested_state = 'started'
    instance.software.setBuildout("""#!/bin/sh
touch worked &&
mkdir -p etc/run &&
(
cat <<'HEREDOC'
#!%(python)s
import signal
def handler(signum, frame):
  print 'Signal handler called with signal', signum
  raise SystemExit
signal.signal(signal.SIGTERM, handler)

while True:
  print "Working"
HEREDOC
)> etc/run/wrapper &&
chmod 755 etc/run/wrapper
""" % {'python': sys.executable})
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(instance.state, 'started')

    computer.sequence = []
    instance.requested_state = 'stopped'
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    self.assertLogContent(wrapper_log, 'Signal handler called with signal 15')
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])
    self.assertEqual(instance.state, 'stopped')

  def test_one_broken_partition_stopped(self):
    """
    Check that, for, an already started instance if stop is requested,
    processes will be stopped even if instance is broken (buildout fails
    to run) but status is still started.
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]

    instance.requested_state = 'started'
    instance.software.setBuildout("""#!/bin/sh
touch worked &&
mkdir -p etc/run &&
(
cat <<'HEREDOC'
#!%(python)s
import signal
def handler(signum, frame):
  print 'Signal handler called with signal', signum
  raise SystemExit
signal.signal(signal.SIGTERM, handler)

while True:
  print "Working"
HEREDOC
)> etc/run/wrapper &&
chmod 755 etc/run/wrapper
""" % {'python': sys.executable})
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertItemsEqual(os.listdir(self.software_root),
                          [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(instance.state, 'started')

    computer.sequence = []
    instance.requested_state = 'stopped'
    instance.software.setBuildout("""#!/bin/sh
exit 1
""")
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_FAIL)
    self.assertItemsEqual(os.listdir(self.instance_root),
                          ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    self.assertLogContent(wrapper_log, 'Signal handler called with signal 15')
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'softwareInstanceError'])
    self.assertEqual(instance.state, 'started')

  def test_one_partition_stopped_started(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'stopped'
    instance.software.setBuildout(WRAPPER_CONTENT)
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)

    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['buildout.cfg', 'etc', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root),
                          [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])
    self.assertEqual('stopped', instance.state)

    instance.requested_state = 'started'
    computer.sequence = []
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.0_wrapper.log', 'etc', 'buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root),
                          [instance.software.software_hash])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual('started', instance.state)

  def test_one_partition_destroyed(self):
    """
    Test that an existing partition with "destroyed" status will only be
    stopped by slapgrid-cp, not processed
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'destroyed'

    dummy_file_name = 'dummy_file'
    with open(os.path.join(instance.partition_path, dummy_file_name), 'w') as dummy_file:
        dummy_file.write('dummy')

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)

    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition), [dummy_file_name])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'stoppedComputerPartition'])
    self.assertEqual('stopped', instance.state)


class TestSlapgridCPWithMasterWatchdog(MasterMixin, unittest.TestCase):

  def setUp(self):
    MasterMixin.setUp(self)
    # Prepare watchdog
    self.watchdog_banged = os.path.join(self._tempdir, 'watchdog_banged')
    watchdog_path = os.path.join(self._tempdir, 'watchdog')
    open(watchdog_path, 'w').write(WATCHDOG_TEMPLATE.format(
        python_path=sys.executable,
        sys_path=sys.path,
        watchdog_banged=self.watchdog_banged
    ))
    os.chmod(watchdog_path, 0o755)
    self.grid.watchdog_path = watchdog_path
    slapos.grid.slapgrid.WATCHDOG_PATH = watchdog_path

  def test_one_failing_daemon_in_service_will_bang_with_watchdog(self):
    """
    Check that a failing service watched by watchdog trigger bang
    1.Prepare computer and set a service named daemon in etc/service
       (to be watched by watchdog). This daemon will fail.
    2.Prepare file for supervisord to call watchdog
       -Set sys.path
       -Monkeypatch computer partition bang
    3.Check damemon is launched
    4.Wait for it to fail
    5.Wait for file generated by monkeypacthed bang to appear
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    partition = computer.instance_list[0]
    partition.requested_state = 'started'
    partition.software.setBuildout(DAEMON_CONTENT)

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(partition.partition_path),
                          ['.0_daemon.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    daemon_log = os.path.join(partition.partition_path, '.0_daemon.log')
    self.assertLogContent(daemon_log, 'Failing')
    self.assertIsCreated(self.watchdog_banged)
    self.assertIn('daemon', open(self.watchdog_banged).read())

  def test_one_failing_daemon_in_run_will_not_bang_with_watchdog(self):
    """
    Check that a failing service watched by watchdog trigger bang
    1.Prepare computer and set a service named daemon in etc/run
       (not watched by watchdog). This daemon will fail.
    2.Prepare file for supervisord to call watchdog
       -Set sys.path
       -Monkeypatch computer partition bang
    3.Check damemon is launched
    4.Wait for it to fail
    5.Check that file generated by monkeypacthed bang do not appear
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    partition = computer.instance_list[0]
    partition.requested_state = 'started'

    RUN_CONTENT = textwrap.dedent("""\
        #!/bin/sh
        mkdir -p etc/run &&
        echo "#!/bin/sh" > etc/run/daemon &&
        echo "touch launched
        touch ./crashed; echo Failing; sleep 1; exit 111;
        " >> etc/run/daemon &&
        chmod 755 etc/run/daemon &&
        touch worked
        """)

    partition.software.setBuildout(RUN_CONTENT)

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root),
                          ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(partition.partition_path),
                          ['.0_daemon.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    daemon_log = os.path.join(partition.partition_path, '.0_daemon.log')
    self.assertLogContent(daemon_log, 'Failing')
    self.assertIsNotCreated(self.watchdog_banged)

  def test_watched_by_watchdog_bang(self):
    """
    Test that a process going to fatal or exited mode in supervisord
    is banged if watched by watchdog
    Certificates used for the bang are also checked
    (ie: watchdog id in process name)
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    certificate_repository_path = os.path.join(self._tempdir, 'partition_pki')
    instance.setCertificate(certificate_repository_path)

    watchdog = Watchdog({
        'master_url': 'https://127.0.0.1/',
        'computer_id': self.computer_id,
        'certificate_repository_path': certificate_repository_path
    })
    for event in watchdog.process_state_events:
      instance.sequence = []
      instance.header_list = []
      headers = {'eventname': event}
      payload = 'processname:%s groupname:%s from_state:RUNNING' % (
          'daemon' + getWatchdogID(), instance.name)
      watchdog.handle_event(headers, payload)
      self.assertEqual(instance.sequence, ['softwareInstanceBang'])
      self.assertEqual(instance.header_list[0]['key'], instance.key)
      self.assertEqual(instance.header_list[0]['certificate'], instance.certificate)

  def test_unwanted_events_will_not_bang(self):
    """
    Test that a process going to a mode not watched by watchdog
    in supervisord is not banged if watched by watchdog
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]

    watchdog = Watchdog({
        'master_url': self.master_url,
        'computer_id': self.computer_id,
        'certificate_repository_path': None
    })
    for event in ['EVENT', 'PROCESS_STATE', 'PROCESS_STATE_RUNNING',
                  'PROCESS_STATE_BACKOFF', 'PROCESS_STATE_STOPPED']:
      computer.sequence = []
      headers = {'eventname': event}
      payload = 'processname:%s groupname:%s from_state:RUNNING' % (
          'daemon' + getWatchdogID(), instance.name)
      watchdog.handle_event(headers, payload)
      self.assertEqual(instance.sequence, [])

  def test_not_watched_by_watchdog_do_not_bang(self):
    """
    Test that a process going to fatal or exited mode in supervisord
    is not banged if not watched by watchdog
    (ie: no watchdog id in process name)
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]

    watchdog = Watchdog({
        'master_url': self.master_url,
        'computer_id': self.computer_id,
        'certificate_repository_path': None
    })
    for event in watchdog.process_state_events:
      computer.sequence = []
      headers = {'eventname': event}
      payload = "processname:%s groupname:%s from_state:RUNNING"\
          % ('daemon', instance.name)
      watchdog.handle_event(headers, payload)
      self.assertEqual(computer.sequence, [])


class TestSlapgridCPPartitionProcessing(MasterMixin, unittest.TestCase):

  def test_partition_timestamp(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    timestamp_path = os.path.join(instance.partition_path, '.timestamp')
    self.setSlapgrid()
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertIn(timestamp, open(timestamp_path).read())
    self.assertEqual(instance.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])

  def test_partition_timestamp_develop(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])

    self.assertEqual(self.launchSlapgrid(develop=True),
                     slapgrid.SLAPGRID_SUCCESS)
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)

    self.assertEqual(instance.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition',
                      'availableComputerPartition', 'stoppedComputerPartition'])

  def test_partition_old_timestamp(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    instance.timestamp = str(int(timestamp) - 1)
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)
    self.assertEqual(instance.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])

  def test_partition_timestamp_new_timestamp(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    instance.timestamp = str(int(timestamp) + 1)
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)
    self.assertEqual(self.launchSlapgrid(), slapgrid.SLAPGRID_SUCCESS)
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition', 'stoppedComputerPartition',
                      'getFullComputerInformation'])

  def test_partition_timestamp_no_timestamp(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.launchSlapgrid()
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])
    self.assertItemsEqual(os.listdir(self.software_root),
                          [instance.software.software_hash])
    instance.timestamp = None
    self.launchSlapgrid()
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition', 'stoppedComputerPartition'])

  def test_partition_periodicity_remove_timestamp(self):
    """
    Check that if periodicity forces run of buildout for a partition, it
    removes the .timestamp file.
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))

    instance.timestamp = timestamp
    instance.requested_state = 'started'
    instance.software.setPeriodicity(1)
    self.grid.force_periodicity = True

    self.launchSlapgrid()
    partition = os.path.join(self.instance_root, '0')
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])

    time.sleep(2)
    # dummify install() so that it doesn't actually do anything so that it
    # doesn't recreate .timestamp.
    instance.install = lambda: None

    self.launchSlapgrid()
    self.assertItemsEqual(os.listdir(partition),
                          ['.timestamp', 'buildout.cfg', 'software_release', 'worked'])

  def test_partition_periodicity_is_not_overloaded_if_forced(self):
    """
    If periodicity file in software directory but periodicity is forced
    periodicity will be the one given by parameter
    1. We set force_periodicity parameter to True
    2. We put a periodicity file in the software release directory
        with an unwanted periodicity
    3. We process partition list and wait more than unwanted periodicity
    4. We relaunch, partition should not be processed
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))

    instance.timestamp = timestamp
    instance.requested_state = 'started'
    unwanted_periodicity = 2
    instance.software.setPeriodicity(unwanted_periodicity)
    self.grid.force_periodicity = True

    self.launchSlapgrid()
    time.sleep(unwanted_periodicity + 1)

    self.setSlapgrid()
    self.grid.force_periodicity = True
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertNotEqual(unwanted_periodicity, self.grid.maximum_periodicity)
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition', 'getFullComputerInformation'])

  def test_one_partition_periodicity_from_file_does_not_disturb_others(self):
    """
    If time between last processing of instance and now is superior
    to periodicity then instance should be proceed
    1. We set a wanted maximum_periodicity in periodicity file in
        in one software release directory and not the other one
    2. We process computer partition and check if wanted_periodicity was
        used as maximum_periodicty
    3. We wait for a time superior to wanted_periodicty
    4. We launch processComputerPartition and check that partition using
        software with periodicity was runned and not the other
    5. We check that modification time of .timestamp was modified
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 20, 20)
    instance0 = computer.instance_list[0]
    timestamp = str(int(time.time() - 5))
    instance0.timestamp = timestamp
    instance0.requested_state = 'started'
    for instance in computer.instance_list[1:]:
      instance.software = \
          computer.software_list[computer.instance_list.index(instance)]
      instance.timestamp = timestamp

    wanted_periodicity = 1
    instance0.software.setPeriodicity(wanted_periodicity)

    self.launchSlapgrid()
    self.assertNotEqual(wanted_periodicity, self.grid.maximum_periodicity)
    last_runtime = os.path.getmtime(
        os.path.join(instance0.partition_path, '.timestamp'))
    time.sleep(wanted_periodicity + 1)
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    time.sleep(1)
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['availableComputerPartition', 'startedComputerPartition',
                      'availableComputerPartition', 'startedComputerPartition',
                      ])
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    self.assertGreater(
        os.path.getmtime(os.path.join(instance0.partition_path, '.timestamp')),
        last_runtime)
    self.assertNotEqual(wanted_periodicity, self.grid.maximum_periodicity)

  def test_one_partition_stopped_is_not_processed_after_periodicity(self):
    """
    Check that periodicity doesn't force processing a partition if it is not
    started.
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 20, 20)
    instance0 = computer.instance_list[0]
    timestamp = str(int(time.time() - 5))
    instance0.timestamp = timestamp
    for instance in computer.instance_list[1:]:
      instance.software = \
          computer.software_list[computer.instance_list.index(instance)]
      instance.timestamp = timestamp

    wanted_periodicity = 1
    instance0.software.setPeriodicity(wanted_periodicity)

    self.launchSlapgrid()
    self.assertNotEqual(wanted_periodicity, self.grid.maximum_periodicity)
    last_runtime = os.path.getmtime(
        os.path.join(instance0.partition_path, '.timestamp'))
    time.sleep(wanted_periodicity + 1)
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    time.sleep(1)
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    self.assertEqual(os.path.getmtime(os.path.join(instance0.partition_path,
                                                   '.timestamp')),
                     last_runtime)
    self.assertNotEqual(wanted_periodicity, self.grid.maximum_periodicity)

  def test_one_partition_destroyed_is_not_processed_after_periodicity(self):
    """
    Check that periodicity doesn't force processing a partition if it is not
    started.
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 20, 20)
    instance0 = computer.instance_list[0]
    timestamp = str(int(time.time() - 5))
    instance0.timestamp = timestamp
    instance0.requested_state = 'stopped'
    for instance in computer.instance_list[1:]:
      instance.software = \
          computer.software_list[computer.instance_list.index(instance)]
      instance.timestamp = timestamp

    wanted_periodicity = 1
    instance0.software.setPeriodicity(wanted_periodicity)

    self.launchSlapgrid()
    self.assertNotEqual(wanted_periodicity, self.grid.maximum_periodicity)
    last_runtime = os.path.getmtime(
        os.path.join(instance0.partition_path, '.timestamp'))
    time.sleep(wanted_periodicity + 1)
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    time.sleep(1)
    instance0.requested_state = 'destroyed'
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    self.assertEqual(os.path.getmtime(os.path.join(instance0.partition_path,
                                                   '.timestamp')),
                     last_runtime)
    self.assertNotEqual(wanted_periodicity, self.grid.maximum_periodicity)

  def test_one_partition_buildout_fail_does_not_disturb_others(self):
    """
    1. We set up two instance one using a corrupted buildout
    2. One will fail but the other one will be processed correctly
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 2, 2)
    instance0 = computer.instance_list[0]
    instance1 = computer.instance_list[1]
    instance1.software = computer.software_list[1]
    instance0.software.setBuildout("""#!/bin/sh
exit 42""")
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['softwareInstanceError'])
    self.assertEqual(instance1.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])

  def test_one_partition_lacking_software_path_does_not_disturb_others(self):
    """
    1. We set up two instance but remove software path of one
    2. One will fail but the other one will be processed correctly
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 2, 2)
    instance0 = computer.instance_list[0]
    instance1 = computer.instance_list[1]
    instance1.software = computer.software_list[1]
    shutil.rmtree(instance0.software.srdir)
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['softwareInstanceError'])
    self.assertEqual(instance1.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])

  def test_one_partition_lacking_software_bin_path_does_not_disturb_others(self):
    """
    1. We set up two instance but remove software bin path of one
    2. One will fail but the other one will be processed correctly
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 2, 2)
    instance0 = computer.instance_list[0]
    instance1 = computer.instance_list[1]
    instance1.software = computer.software_list[1]
    shutil.rmtree(instance0.software.srbindir)
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['softwareInstanceError'])
    self.assertEqual(instance1.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])

  def test_one_partition_lacking_path_does_not_disturb_others(self):
    """
    1. We set up two instances but remove path of one
    2. One will fail but the other one will be processed correctly
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 2, 2)
    instance0 = computer.instance_list[0]
    instance1 = computer.instance_list[1]
    instance1.software = computer.software_list[1]
    shutil.rmtree(instance0.partition_path)
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['softwareInstanceError'])
    self.assertEqual(instance1.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])

  def test_one_partition_buildout_fail_is_correctly_logged(self):
    """
    1. We set up an instance using a corrupted buildout
    2. It will fail, make sure that whole log is sent to master
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 1, 1)
    instance = computer.instance_list[0]

    line1 = "Nerdy kitten: Can I has a process crash?"
    line2 = "Cedric: Sure, here it is."
    instance.software.setBuildout("""#!/bin/sh
echo %s; echo %s; exit 42""" % (line1, line2))
    self.launchSlapgrid()
    self.assertEqual(instance.sequence, ['softwareInstanceError'])
    # We don't care of actual formatting, we just want to have full log
    self.assertIn(line1, instance.error_log)
    self.assertIn(line2, instance.error_log)
    self.assertIn('Failed to run buildout', instance.error_log)


class TestSlapgridUsageReport(MasterMixin, unittest.TestCase):
  """
  Test suite about slapgrid-ur
  """

  def test_slapgrid_destroys_instance_to_be_destroyed(self):
    """
    Test than an instance in "destroyed" state is correctly destroyed
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    instance.software.setBuildout(WRAPPER_CONTENT)
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(instance.state, 'started')

    # Then destroy the instance
    computer.sequence = []
    instance.requested_state = 'destroyed'
    self.assertEqual(self.grid.agregateAndSendUsage(), slapgrid.SLAPGRID_SUCCESS)
    # Assert partition directory is empty
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path), [])
    self.assertItemsEqual(os.listdir(self.software_root),
                          [instance.software.software_hash])
    # Assert supervisor stopped process
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertIsNotCreated(wrapper_log)

    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'stoppedComputerPartition',
                      'destroyedComputerPartition'])
    self.assertEqual(instance.state, 'destroyed')

  def test_partition_list_is_complete_if_empty_destroyed_partition(self):
    """
    Test that an empty partition with destroyed state but with SR informations
    Is correctly destroyed
    Axiom: each valid partition has a state and a software_release.
    Scenario:
    1. Simulate computer containing one "destroyed" partition but with valid SR
    2. See if it destroyed
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]

    computer.sequence = []
    instance.requested_state = 'destroyed'
    self.assertEqual(self.grid.agregateAndSendUsage(), slapgrid.SLAPGRID_SUCCESS)
    # Assert partition directory is empty
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path), [])
    self.assertItemsEqual(os.listdir(self.software_root),
                          [instance.software.software_hash])
    # Assert supervisor stopped process
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertIsNotCreated(wrapper_log)

    self.assertEqual(
        computer.sequence,
        ['getFullComputerInformation', 'stoppedComputerPartition', 'destroyedComputerPartition'])

  def test_slapgrid_not_destroy_bad_instance(self):
    """
    Checks that slapgrid-ur don't destroy instance not to be destroyed.
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    instance.software.setBuildout(WRAPPER_CONTENT)
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual('started', instance.state)

    # Then run usage report and see if it is still working
    computer.sequence = []
    self.assertEqual(self.grid.agregateAndSendUsage(), slapgrid.SLAPGRID_SUCCESS)
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path),
                          ['.0_wrapper.log', 'buildout.cfg', 'etc', 'software_release', 'worked'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    self.assertLogContent(wrapper_log, 'Working')
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation'])
    self.assertEqual('started', instance.state)

  def test_slapgrid_instance_ignore_free_instance(self):
    """
    Test than a free instance (so in "destroyed" state, but empty, without
    software_release URI) is ignored by slapgrid-cp.
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.software.name = None

    computer.sequence = []
    instance.requested_state = 'destroyed'
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    # Assert partition directory is empty
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path), [])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence, ['getFullComputerInformation'])

  def test_slapgrid_report_ignore_free_instance(self):
    """
    Test than a free instance (so in "destroyed" state, but empty, without
    software_release URI) is ignored by slapgrid-ur.
    """
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.software.name = None

    computer.sequence = []
    instance.requested_state = 'destroyed'
    self.assertEqual(self.grid.agregateAndSendUsage(), slapgrid.SLAPGRID_SUCCESS)
    # Assert partition directory is empty
    self.assertItemsEqual(os.listdir(self.instance_root), ['0', 'etc', 'var'])
    self.assertItemsEqual(os.listdir(instance.partition_path), [])
    self.assertItemsEqual(os.listdir(self.software_root), [instance.software.software_hash])
    self.assertEqual(computer.sequence, ['getFullComputerInformation'])


class TestSlapgridSoftwareRelease(MasterMixin, unittest.TestCase):
  def test_one_software_buildout_fail_is_correctly_logged(self):
    """
    1. We set up a software using a corrupted buildout
    2. It will fail, make sure that whole log is sent to master
    """
    computer = ComputerForTest(self.software_root, self.instance_root, 1, 1)
    software = computer.software_list[0]

    line1 = "Nerdy kitten: Can I has a process crash?"
    line2 = "Cedric: Sure, here it is."
    software.setBuildout("""#!/bin/sh
echo %s; echo %s; exit 42""" % (line1, line2))
    self.launchSlapgridSoftware()
    self.assertEqual(software.sequence,
                     ['buildingSoftwareRelease', 'softwareReleaseError'])
    # We don't care of actual formatting, we just want to have full log
    self.assertIn(line1, software.error_log)
    self.assertIn(line2, software.error_log)
    self.assertIn('Failed to run buildout', software.error_log)


class SlapgridInitialization(unittest.TestCase):
  """
  "Abstract" class setting setup and teardown for TestSlapgridArgumentTuple
  and TestSlapgridConfigurationFile.
  """

  def setUp(self):
    """
      Create the minimun default argument and configuration.
    """
    self.certificate_repository_path = tempfile.mkdtemp()
    self.fake_file_descriptor = tempfile.NamedTemporaryFile()
    self.slapos_config_descriptor = tempfile.NamedTemporaryFile()
    self.slapos_config_descriptor.write("""
[slapos]
software_root = /opt/slapgrid
instance_root = /srv/slapgrid
master_url = https://slap.vifib.com/
computer_id = your computer id
buildout = /path/to/buildout/binary
""")
    self.slapos_config_descriptor.seek(0)
    self.default_arg_tuple = (
        '--cert_file', self.fake_file_descriptor.name,
        '--key_file', self.fake_file_descriptor.name,
        '--master_ca_file', self.fake_file_descriptor.name,
        '--certificate_repository_path', self.certificate_repository_path,
        '-c', self.slapos_config_descriptor.name, '--now')

    self.signature_key_file_descriptor = tempfile.NamedTemporaryFile()
    self.signature_key_file_descriptor.seek(0)

  def tearDown(self):
    """
      Removing the temp file.
    """
    self.fake_file_descriptor.close()
    self.slapos_config_descriptor.close()
    self.signature_key_file_descriptor.close()
    shutil.rmtree(self.certificate_repository_path, True)


class TestSlapgridArgumentTuple(SlapgridInitialization):
  """
  Test suite about arguments given to slapgrid command.
  """

  def test_empty_argument_tuple(self):
    """
      Raises if the argument list if empty and without configuration file.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    # XXX: SystemExit is too generic exception, it is only known that
    #      something is wrong
    self.assertRaises(SystemExit, parser, *())

  def test_default_argument_tuple(self):
    """
      Check if we can have the slapgrid object returned with the minimum
      arguments.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    return_list = parser(*self.default_arg_tuple)
    self.assertEquals(2, len(return_list))

  def test_signature_private_key_file_non_exists(self):
    """
      Raises if the  signature_private_key_file does not exists.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = ("--signature_private_key_file",
                      "/non/exists/path") + self.default_arg_tuple
    self.assertRaisesRegexp(RuntimeError,
                            "File '/non/exists/path' does not exist.",
                            parser, *argument_tuple)

  def test_signature_private_key_file(self):
    """
      Check if the signature private key argument value is available on
      slapgrid object.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = ("--signature_private_key_file",
                      self.signature_key_file_descriptor.name) + self.default_arg_tuple
    slapgrid_object = parser(*argument_tuple)[0]
    self.assertEquals(self.signature_key_file_descriptor.name,
                      slapgrid_object.signature_private_key_file)

  def test_backward_compatibility_all(self):
    """
      Check if giving --all triggers "develop" option.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    slapgrid_object = parser('--all', *self.default_arg_tuple)[0]
    self.assertTrue(slapgrid_object.develop)

  def test_backward_compatibility_not_all(self):
    """
      Check if not giving --all neither --develop triggers "develop"
      option to be False.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    slapgrid_object = parser(*self.default_arg_tuple)[0]
    self.assertFalse(slapgrid_object.develop)

  def test_force_periodicity_if_periodicity_not_given(self):
    """
      Check if not giving --maximum-periodicity triggers "force_periodicity"
      option to be false.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    slapgrid_object = parser(*self.default_arg_tuple)[0]
    self.assertFalse(slapgrid_object.force_periodicity)

  def test_force_periodicity_if_periodicity_given(self):
    """
      Check if giving --maximum-periodicity triggers "force_periodicity" option.
    """
    parser = parseArgumentTupleAndReturnSlapgridObject
    slapgrid_object = parser('--maximum-periodicity', '40', *self.default_arg_tuple)[0]
    self.assertTrue(slapgrid_object.force_periodicity)


class TestSlapgridConfigurationFile(SlapgridInitialization):

  def test_upload_binary_cache_blacklist(self):
    """
      Check if giving --upload-to-binary-cache-url-blacklist triggers option.
    """
    self.slapos_config_descriptor.write("""
[slapos]
software_root = /opt/slapgrid
instance_root = /srv/slapgrid
master_url = https://slap.vifib.com/
computer_id = your computer id
buildout = /path/to/buildout/binary
[networkcache]
upload-to-binary-cache-url-blacklist =
  http://1
  http://2/bla
""")
    self.slapos_config_descriptor.seek(0)
    slapgrid_object = parseArgumentTupleAndReturnSlapgridObject(
        *self.default_arg_tuple)[0]
    self.assertEqual(
        slapgrid_object.upload_to_binary_cache_url_blacklist,
        ['http://1', 'http://2/bla']
    )
    self.assertEqual(
        slapgrid_object.download_from_binary_cache_url_blacklist,
        []
    )

  def test_download_binary_cache_blacklist(self):
    """
      Check if giving --download-from-binary-cache-url-blacklist triggers option.
    """
    self.slapos_config_descriptor.write("""
[slapos]
software_root = /opt/slapgrid
instance_root = /srv/slapgrid
master_url = https://slap.vifib.com/
computer_id = your computer id
buildout = /path/to/buildout/binary
[networkcache]
download-from-binary-cache-url-blacklist =
  http://1
  http://2/bla
""")
    self.slapos_config_descriptor.seek(0)
    slapgrid_object = parseArgumentTupleAndReturnSlapgridObject(
        *self.default_arg_tuple)[0]
    self.assertEqual(
        slapgrid_object.upload_to_binary_cache_url_blacklist,
        []
    )
    self.assertEqual(
        slapgrid_object.download_from_binary_cache_url_blacklist,
        ['http://1', 'http://2/bla']
    )

  def test_upload_download_binary_cache_blacklist(self):
    """
      Check if giving both --download-from-binary-cache-url-blacklist
      and --upload-to-binary-cache-url-blacklist triggers options.
    """
    self.slapos_config_descriptor.write("""
[slapos]
software_root = /opt/slapgrid
instance_root = /srv/slapgrid
master_url = https://slap.vifib.com/
computer_id = your computer id
buildout = /path/to/buildout/binary
[networkcache]
upload-to-binary-cache-url-blacklist =
  http://1
  http://2/bla
download-from-binary-cache-url-blacklist =
  http://3
  http://4/bla
""")
    self.slapos_config_descriptor.seek(0)
    slapgrid_object = parseArgumentTupleAndReturnSlapgridObject(
        *self.default_arg_tuple)[0]
    self.assertEqual(
        slapgrid_object.upload_to_binary_cache_url_blacklist,
        ['http://1', 'http://2/bla']
    )
    self.assertEqual(
        slapgrid_object.download_from_binary_cache_url_blacklist,
        ['http://3', 'http://4/bla']
    )

  def test_backward_compatibility_download_binary_cache_blacklist(self):
    """
      Check if giving both --binary-cache-url-blacklist
      and --upload-to-binary-cache-blacklist triggers options.
    """
    self.slapos_config_descriptor.write("""
[slapos]
software_root = /opt/slapgrid
instance_root = /srv/slapgrid
master_url = https://slap.vifib.com/
computer_id = your computer id
buildout = /path/to/buildout/binary
[networkcache]
binary-cache-url-blacklist =
  http://1
  http://2/bla
""")
    self.slapos_config_descriptor.seek(0)
    slapgrid_object = parseArgumentTupleAndReturnSlapgridObject(
        *self.default_arg_tuple)[0]
    self.assertEqual(
        slapgrid_object.upload_to_binary_cache_url_blacklist,
        []
    )
    self.assertEqual(
        slapgrid_object.download_from_binary_cache_url_blacklist,
        ['http://1', 'http://2/bla']
    )


class TestSlapgridCPWithMasterPromise(MasterMixin, unittest.TestCase):
  def test_one_failing_promise(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    worked_file = os.path.join(instance.partition_path, 'fail_worked')
    fail = textwrap.dedent("""\
            #!/usr/bin/env sh
            touch "%s"
            exit 127""" % worked_file)
    instance.setPromise('fail', fail)
    self.assertEqual(self.grid.processComputerPartitionList(),
                     slapos.grid.slapgrid.SLAPGRID_PROMISE_FAIL)
    self.assertTrue(os.path.isfile(worked_file))
    self.assertTrue(instance.error)
    self.assertNotEqual('started', instance.state)

  def test_one_succeeding_promise(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    self.fake_waiting_time = 0.1
    worked_file = os.path.join(instance.partition_path, 'succeed_worked')
    succeed = textwrap.dedent("""\
            #!/usr/bin/env sh
            touch "%s"
            exit 0""" % worked_file)
    instance.setPromise('succeed', succeed)
    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    self.assertTrue(os.path.isfile(worked_file))

    self.assertFalse(instance.error)
    self.assertEqual(instance.state, 'started')

  def test_stderr_has_been_sent(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    httplib.HTTPConnection._callback = computer.getServerResponse()

    instance.requested_state = 'started'
    self.fake_waiting_time = 0.5

    promise_path = os.path.join(instance.partition_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'stderr_writer')
    worked_file = os.path.join(instance.partition_path, 'stderr_worked')
    with open(succeed, 'w') as f:
      f.write(textwrap.dedent("""\
            #!/usr/bin/env sh
            touch "%s"
            echo Error 1>&2
            exit 127""" % worked_file))
    os.chmod(succeed, 0o777)
    self.assertEqual(self.grid.processComputerPartitionList(),
                     slapos.grid.slapgrid.SLAPGRID_PROMISE_FAIL)
    self.assertTrue(os.path.isfile(worked_file))

    self.assertEqual(instance.error_log[-5:], 'Error')
    self.assertTrue(instance.error)
    self.assertIsNone(instance.state)

  def test_timeout_works(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]

    instance.requested_state = 'started'
    self.fake_waiting_time = 0.1

    promise_path = os.path.join(instance.partition_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'timed_out_promise')
    worked_file = os.path.join(instance.partition_path, 'timed_out_worked')
    with open(succeed, 'w') as f:
      f.write(textwrap.dedent("""\
            #!/usr/bin/env sh
            touch "%s"
            sleep 5
            exit 0""" % worked_file))
    os.chmod(succeed, 0o777)
    self.assertEqual(self.grid.processComputerPartitionList(),
                     slapos.grid.slapgrid.SLAPGRID_PROMISE_FAIL)
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(instance.error)
    self.assertIsNone(instance.state)

  def test_two_succeeding_promises(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'

    self.fake_waiting_time = 0.1

    for i in range(2):
      worked_file = os.path.join(instance.partition_path, 'succeed_%s_worked' % i)
      succeed = textwrap.dedent("""\
            #!/usr/bin/env sh
            touch "%s"
            exit 0""" % worked_file)
      instance.setPromise('succeed_%s' % i, succeed)

    self.assertEqual(self.grid.processComputerPartitionList(), slapgrid.SLAPGRID_SUCCESS)
    for i in range(2):
      worked_file = os.path.join(instance.partition_path, 'succeed_%s_worked' % i)
      self.assertTrue(os.path.isfile(worked_file))
    self.assertFalse(instance.error)
    self.assertEqual(instance.state, 'started')

  def test_one_succeeding_one_failing_promises(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    self.fake_waiting_time = 0.1

    for i in range(2):
      worked_file = os.path.join(instance.partition_path, 'promise_worked_%d' % i)
      lockfile = os.path.join(instance.partition_path, 'lock')
      promise = textwrap.dedent("""\
                #!/usr/bin/env sh
                touch "%(worked_file)s"
                if [ ! -f %(lockfile)s ]
                then
                  touch "%(lockfile)s"
                  exit 0
                else
                  exit 127
                fi""" % {
          'worked_file': worked_file,
          'lockfile': lockfile
      })
      instance.setPromise('promise_%s' % i, promise)
    self.assertEqual(self.grid.processComputerPartitionList(),
                     slapos.grid.slapgrid.SLAPGRID_PROMISE_FAIL)
    self.assertEquals(instance.error, 1)
    self.assertNotEqual('started', instance.state)

  def test_one_succeeding_one_timing_out_promises(self):
    computer = ComputerForTest(self.software_root, self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    self.fake_waiting_time = 0.1
    for i in range(2):
      worked_file = os.path.join(instance.partition_path, 'promise_worked_%d' % i)
      lockfile = os.path.join(instance.partition_path, 'lock')
      promise = textwrap.dedent("""\
                #!/usr/bin/env sh
                touch "%(worked_file)s"
                if [ ! -f %(lockfile)s ]
                then
                  touch "%(lockfile)s"
                else
                  sleep 5
                fi
                exit 0""" % {
          'worked_file': worked_file,
          'lockfile': lockfile}
      )
      instance.setPromise('promise_%d' % i, promise)

    self.assertEqual(self.grid.processComputerPartitionList(),
                     slapos.grid.slapgrid.SLAPGRID_PROMISE_FAIL)

    self.assertEquals(instance.error, 1)
    self.assertNotEqual(instance.state, 'started')
