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

from slapos.grid import slapgrid
import httplib
import logging
import os
import shutil
import signal
import slapos.slap.slap
import socket
import sys
import tempfile
import time
import unittest
import urlparse
import xml_marshaller

WRAPPER_CONTENT = """#!/bin/sh
touch worked &&
mkdir -p etc/run &&
echo "#!/bin/sh" > etc/run/wrapper &&
echo "while :; do echo "Working\\nWorking\\n" ; sleep 0.1; done" >> etc/run/wrapper &&
chmod 755 etc/run/wrapper
"""

class BasicMixin:
  def assertSortedListEqual(self, list1, list2, msg=None):
    self.assertListEqual(sorted(list1), sorted(list2), msg)

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
    self.grid = slapgrid.Slapgrid(self.software_root, self.instance_root,
      self.master_url, self.computer_id, self.supervisord_socket,
      self.supervisord_configuration_path, self.usage_report_periodicity,
      self.buildout, develop=develop)

  def launchSlapgrid(self,develop=False):
    self.setSlapgrid(develop=develop)
    return self.grid.processComputerPartitionList()

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

    self.saved_httplib = dict()

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
    self.software_list = range(0,self.software_amount)
    for i in self.software_list:
      name = str(i)
      self.software_list[i] = SoftwareForTest(self.software_root, name=name)

  def setInstances(self):
    """
    Will set requested amount of instance giving them by default first software
    """
    self.instance_list = range(0, self.instance_amount)
    for i in self.instance_list:
      name = str(i)
      if len(self.software_list) is not 0:
        software = self.software_list[0]
      else:
        software = None
      self.instance_list[i] = InstanceForTest(self.instance_root, name=name,
                                 software=software)

  def getComputer (self, computer_id):
    """
    Will return current requested state of computer
    """
    slap_computer = slapos.slap.Computer(computer_id)
    slap_computer._software_release_list = []
    slap_computer._computer_partition_list = []
    for instance in self.instance_list:
      slap_computer._computer_partition_list.append(
        instance.getInstance(computer_id))
    return slap_computer

  def setServerResponse(self):
    httplib.HTTPConnection._callback = self.getServerResponse()

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
      if parsed_url.path == 'getFullComputerInformation' and \
            'computer_id' in parsed_qs:
        slap_computer = self.getComputer(parsed_qs['computer_id'][0])
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if method == 'POST' and 'computer_partition_id' in parsed_qs:
        instance = self.instance_list[int(parsed_qs['computer_partition_id'][0])]
        instance.sequence.append(parsed_url.path)
        if parsed_url.path == 'availableComputerPartition':
          return (200, {}, '')
        if parsed_url.path == 'startedComputerPartition':
          instance.state = 'started'
          return (200, {}, '')
        if parsed_url.path == 'stoppedComputerPartition':
          instance.state = 'stopped'
          return (200, {}, '')
        if parsed_url.path == 'softwareInstanceError':
          instance.error_log = '\n'.join([line for line \
                                   in parsed_qs['error_log'][0].splitlines()
                                 if 'dropPrivileges' not in line])
          instance.error = True
          return (200, {}, '')
        else:
          return (404, {}, '')
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
    self.name = name
    self.partition_path = os.path.join(self.instance_root, self.name)
    os.mkdir(self.partition_path, 0750)
    self.timestamp = None

  def getInstance (self, computer_id):
    """
    Will return current requested state of instance
    """
    partition = slapos.slap.ComputerPartition(computer_id, self.name)
    partition._software_release_document = self.getSoftwareRelease()
    partition._requested_state = self.requested_state
    if self.software is not None:
      if self.timestamp is not None :
        partition._parameter_dict = {'timestamp': self.timestamp}
    return partition

  def getSoftwareRelease (self):
    """
    Return software release for Instance
    """
    if self.software is not None:
      sr = slapos.slap.SoftwareRelease()
      sr._software_release = self.software.name
      return sr
    else: return None

  def setPromise (self, promise_name, promise_content):
    """
    This function will set promise and return its path
    """
    promise_path = os.path.join(self.partition_path, 'etc', 'promise')
    if not os.path.isdir(promise_path):
      os.makedirs(promise_path)
    promise = os.path.join(promise_path,promise_name)
    open(promise, 'w').write(promise_content)
    os.chmod(promise, 0777)


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
    self.software_hash = \
        slapos.grid.utils.getSoftwareUrlHash(self.name)
    self.srdir = os.path.join(self.software_root, self.software_hash)
    os.mkdir(self.srdir)
    self.setTemplateCfg()
    self.srbindir = os.path.join(self.srdir, 'bin')
    os.mkdir(self.srbindir)
    self.setBuildout()

  def setTemplateCfg (self,template = """[buildout]"""):
    """
    Set template.cfg
    """
    open(os.path.join(self.srdir, 'template.cfg'), 'w').write(template)

  def setBuildout (self,buildout = """#!/bin/sh
touch worked"""):
    """
    Set a buildout exec in bin
    """
    open(os.path.join(self.srbindir, 'buildout'), 'w').write(buildout)
    os.chmod(os.path.join(self.srbindir, 'buildout'), 0755)

  def setPeriodicity(self,periodicity):
    """
    Set a periodicity file
    """
    open(os.path.join(self.srdir, 'periodicity'), 'w').write(
      """%s""" % (periodicity))



class TestSlapgridCPWithMaster(MasterMixin, unittest.TestCase):

  def test_nothing_to_do(self):

    computer = ComputerForTest(self.software_root,self.instance_root,0,0)

    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['etc', 'var'])
    self.assertSortedListEqual(os.listdir(self.software_root), [])

  def test_one_partition(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['worked',
      'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])

  def test_one_partition_instance_cfg(self):
    """
    Check that slapgrid processes instance is profile is not named
    "template.cfg" but "instance.cfg".
    """
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['worked',
      'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])

  def test_one_free_partition(self):
    """
    Test if slapgrid don't process "free" partition
    """
    computer = ComputerForTest(self.software_root,self.instance_root,
                               software_amount = 0)
    partition = computer.instance_list[0]
    partition.requested_state = 'destroyed'
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0','etc', 'var'])
    self.assertSortedListEqual(os.listdir(partition.partition_path), [])
    self.assertSortedListEqual(os.listdir(self.software_root), [])
    self.assertEqual(partition.sequence, [])

  def test_one_partition_started(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    partition = computer.instance_list[0]
    partition.requested_state = 'started'
    partition.software.setBuildout(WRAPPER_CONTENT)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(partition.partition_path),
                               ['.0_wrapper.log','worked', 'buildout.cfg', 'etc'])
    tries = 10
    wrapper_log = os.path.join(partition.partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [partition.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(partition.state,'started')


  def test_one_partition_started_stopped(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
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
""" % dict(python = sys.executable))
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(instance.partition_path), ['.0_wrapper.log',
      'worked', 'buildout.cfg', 'etc'])
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    tries = 10
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    os.path.getsize(wrapper_log)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(instance.state,'started')

    computer.sequence = []
    instance.requested_state = 'stopped'
    self.assertTrue(self.launchSlapgrid())
    self.assertSortedListEqual(os.listdir(self.instance_root),
                               ['0', 'etc', 'var'])
    self.assertSortedListEqual(
      os.listdir(instance.partition_path),
      ['.0_wrapper.log', '.0_wrapper.log.1', 'worked', 'buildout.cfg', 'etc'])
    tries = 10
    expected_text = 'Signal handler called with signal 15'
    while tries > 0:
      tries -= 1
      found = expected_text in open(wrapper_log, 'r').read()
      if found:
        break
      time.sleep(0.2)
    self.assertTrue(found)
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])
    self.assertEqual(instance.state,'stopped')


  def test_one_partition_stopped_started(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'stopped'
    instance.software.setBuildout(WRAPPER_CONTENT)
    self.assertTrue(self.grid.processComputerPartitionList())

    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['worked', 'etc',
      'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])
    self.assertEqual('stopped',instance.state)

    instance.requested_state = 'started'
    computer.sequence = []
    self.assertTrue(self.launchSlapgrid())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['.0_wrapper.log',
      'worked', 'etc', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    tries = 10
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual('started',instance.state)


class TestSlapgridCPPartitionProcessing (MasterMixin, unittest.TestCase):

  def test_partition_timestamp(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(
        os.listdir(partition), ['.timestamp', 'worked', 'buildout.cfg'])
    self.assertSortedListEqual(
        os.listdir(self.software_root), [instance.software.software_hash])
    timestamp_path = os.path.join(instance.partition_path, '.timestamp')
    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(timestamp in open(timestamp_path,'r').read())
    self.assertEqual(instance.sequence,
                     ['availableComputerPartition',
                      'stoppedComputerPartition'])


  def test_partition_timestamp_develop(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(
        os.listdir(partition), ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(
        os.listdir(self.software_root), [instance.software.software_hash])

    self.assertTrue(self.launchSlapgrid(develop=True))
    self.assertTrue(self.launchSlapgrid())

    self.assertEqual(instance.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition',
                      'availableComputerPartition','stoppedComputerPartition'])

  def test_partition_old_timestamp(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition),
                               ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    instance.timestamp = str(int(timestamp) - 1)
    self.assertTrue(self.launchSlapgrid())
    self.assertEqual(instance.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition'])


  def test_partition_timestamp_new_timestamp(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.assertTrue(self.launchSlapgrid())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition),
                               ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    instance.timestamp = str(int(timestamp)+1)
    self.assertTrue(self.launchSlapgrid())
    self.assertTrue(self.launchSlapgrid())
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition','stoppedComputerPartition',
                      'getFullComputerInformation'])

  def test_partition_timestamp_no_timestamp(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))
    instance.timestamp = timestamp

    self.launchSlapgrid()
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition),
                               ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    instance.timestamp = None
    self.launchSlapgrid()
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition','stoppedComputerPartition',])


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
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    timestamp = str(int(time.time()))

    instance.timestamp = timestamp
    unwanted_periodicity = 2
    instance.software.setPeriodicity(unwanted_periodicity)
    self.grid.force_periodicity = True

    self.launchSlapgrid()
    time.sleep(unwanted_periodicity + 1)

    self.setSlapgrid()
    self.grid.force_periodicity = True
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertNotEqual(unwanted_periodicity,self.grid.maximum_periodicity)
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation'])


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
    computer = ComputerForTest(self.software_root,self.instance_root,20,20)
    instance0 = computer.instance_list[0]
    timestamp = str(int(time.time()-5))
    instance0.timestamp = timestamp
    for instance in computer.instance_list[1:]:
      instance.software = \
          computer.software_list[computer.instance_list.index(instance)]
      instance.timestamp = timestamp

    wanted_periodicity = 3
    instance0.software.setPeriodicity(wanted_periodicity)

    self.launchSlapgrid()
    self.assertNotEqual(wanted_periodicity,self.grid.maximum_periodicity)
    last_runtime = os.path.getmtime(
      os.path.join(instance0.partition_path, '.timestamp'))
    time.sleep(wanted_periodicity + 1)
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    self.launchSlapgrid()
    self.assertEqual(instance0.sequence,
                     ['availableComputerPartition', 'stoppedComputerPartition',
                      'availableComputerPartition', 'stoppedComputerPartition',
                      ])
    for instance in computer.instance_list[1:]:
      self.assertEqual(instance.sequence,
                       ['availableComputerPartition', 'stoppedComputerPartition'])
    self.assertGreater(
      os.path.getmtime(os.path.join(instance0.partition_path,'.timestamp')),
      last_runtime)
    self.assertNotEqual(wanted_periodicity,self.grid.maximum_periodicity)


class TestSlapgridUsageReport(MasterMixin, unittest.TestCase):
  """
  Test suite about slapgrid-ur
  """

  def test_slapgrid_destroys_instance_to_be_destroyed(self):
    """
    Test than an instance in "destroyed" state is correctly destroyed
    """
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    instance.software.setBuildout(WRAPPER_CONTENT)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(instance.partition_path), ['.0_wrapper.log',
      'worked', 'buildout.cfg', 'etc'])
    tries = 10
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual(instance.state,'started')

    # Then destroy the instance
    computer.sequence = []
    instance.requested_state = 'destroyed'
    self.assertTrue(self.grid.agregateAndSendUsage())
    # Assert partition directory is empty
    self.assertSortedListEqual(os.listdir(self.instance_root),
                               ['0', 'etc', 'var'])
    self.assertSortedListEqual(os.listdir(instance.partition_path), [])
    self.assertSortedListEqual(os.listdir(self.software_root),
                               [instance.software.software_hash])
    # Assert supervisor stopped process
    tries = 10
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    exists = False
    while tries > 0:
      tries -= 1
      if os.path.exists(wrapper_log):
        exists = True
        break
      time.sleep(0.2)
    self.assertFalse(exists)

    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'stoppedComputerPartition',
                      'destroyedComputerPartition'])
    self.assertEqual(instance.state,'stopped')

  def test_slapgrid_not_destroy_bad_instance(self):
    """
    Checks that slapgrid-ur don't destroy instance not to be destroyed.
    """
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    instance.software.setBuildout(WRAPPER_CONTENT)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root),
                               ['0', 'etc', 'var'])
    self.assertSortedListEqual(os.listdir(instance.partition_path),
                               ['.0_wrapper.log', 'worked', 'buildout.cfg', 'etc'])
    tries = 20
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [instance.software.software_hash])
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation',
                      'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertEqual('started',instance.state)

    # Then run usage report and see if it is still working
    computer.sequence = []
    self.assertTrue(self.grid.agregateAndSendUsage())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(
      os.listdir(instance.partition_path),
      ['.0_wrapper.log', 'worked', 'buildout.cfg', 'etc'])
    tries = 10
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(instance.partition_path),
                               ['.0_wrapper.log', 'worked', 'buildout.cfg', 'etc'])
    tries = 20
    wrapper_log = os.path.join(instance.partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertEqual(computer.sequence,
                     ['getFullComputerInformation'])
    self.assertEqual('started',instance.state)



class TestSlapgridArgumentTuple(unittest.TestCase):
  """
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
""" % dict(fake_file=self.fake_file_descriptor.name))
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

  def test_empty_argument_tuple(self):
    """
      Raises if the argument list if empty and without configuration file.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    # XXX: SystemExit is too generic exception, it is only known that
    #      something is wrong
    self.assertRaises(SystemExit, parser, *())

  def test_default_argument_tuple(self):
    """
      Check if we can have the slapgrid object returned with the minimum
      arguments.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    return_list = parser(*self.default_arg_tuple)
    self.assertEquals(2, len(return_list))

  def test_signature_private_key_file_non_exists(self):
    """
      Raises if the  signature_private_key_file does not exists.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = ("--signature_private_key_file", "/non/exists/path") + \
                      self.default_arg_tuple
    # XXX: SystemExit is too generic exception, it is only known that
    #      something is wrong
    self.assertRaises(SystemExit, parser, *argument_tuple)

  def test_signature_private_key_file(self):
    """
      Check if the signature private key argument value is available on
      slapgrid object.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = ("--signature_private_key_file",
                      self.signature_key_file_descriptor.name) + \
                      self.default_arg_tuple
    slapgrid_object = parser(*argument_tuple)[0]
    self.assertEquals(self.signature_key_file_descriptor.name,
                          slapgrid_object.signature_private_key_file)

  def test_backward_compatibility_all(self):
    """
      Check if giving --all triggers "develop" option.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = ("--all",) + self.default_arg_tuple
    slapgrid_object = parser(*argument_tuple)[0]
    self.assertTrue(slapgrid_object.develop)

  def test_backward_compatibility_not_all(self):
    """
      Check if not giving --all neither --develop triggers "develop"
      option to be False.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = self.default_arg_tuple
    slapgrid_object = parser(*argument_tuple)[0]
    self.assertFalse(slapgrid_object.develop)

  def test_force_periodicity_if_periodicity_not_given(self):
    """
      Check if not giving --maximum-periodicity triggers "force_periodicity"
      option to be false.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = self.default_arg_tuple
    slapgrid_object = parser(*argument_tuple)[0]
    self.assertFalse(slapgrid_object.force_periodicity)

  def test_force_periodicity_if_periodicity_given(self):
    """
      Check if giving --maximum-periodicity triggers "force_periodicity" option.
    """
    parser = slapgrid.parseArgumentTupleAndReturnSlapgridObject
    argument_tuple = ("--maximum-periodicity","40") + self.default_arg_tuple
    slapgrid_object = parser(*argument_tuple)[0]
    self.assertTrue(slapgrid_object.force_periodicity)

class TestSlapgridCPWithMasterPromise(MasterMixin, unittest.TestCase):
  def test_one_failing_promise(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    worked_file = os.path.join(instance.partition_path, 'fail_worked')
    fail = ("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 127""" % {'worked_file': worked_file})
    instance.setPromise('fail',fail)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))
    self.assertTrue(instance.error)
    self.assertNotEqual('started',instance.state)

  def test_one_succeeding_promise(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    self.fake_waiting_time = 0.2
    worked_file = os.path.join(instance.partition_path, 'succeed_worked')
    succeed = ("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 0""" % {'worked_file': worked_file})
    instance.setPromise('succeed',succeed)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertFalse(instance.error)
    self.assertEqual(instance.state,'started')

  def test_stderr_has_been_sent(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    httplib.HTTPConnection._callback = computer.getServerResponse()

    instance.requested_state = 'started'
    self.fake_waiting_time = 0.5

    promise_path = os.path.join(instance.partition_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'stderr_writer')
    worked_file = os.path.join(instance.partition_path, 'stderr_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
echo Error 1>&2
exit 127""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertEqual(instance.error_log, 'Error')
    self.assertTrue(instance.error)
    self.assertIsNone(instance.state)


  def test_timeout_works(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]

    instance.requested_state = 'started'
    self.fake_waiting_time = 0.2

    promise_path = os.path.join(instance.partition_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'timed_out_promise')
    worked_file = os.path.join(instance.partition_path, 'timed_out_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
sleep 5
exit 0""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(instance.error)
    self.assertIsNone(instance.state)

  def test_two_succeeding_promises(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'

    self.fake_waiting_time = 0.2

    for i in range (0,2):
      worked_file = os.path.join(instance.partition_path, 'succeed_%s_worked' % i)
      succeed = ("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 0""" % {'worked_file': worked_file})
      instance.setPromise('succeed_%s' % i, succeed)

    self.assertTrue(self.grid.processComputerPartitionList())
    for i in range(0,2):
      worked_file = os.path.join(instance.partition_path, 'succeed_%s_worked' % i)
      self.assertTrue(os.path.isfile(worked_file))
    self.assertFalse(instance.error)
    self.assertEqual(instance.state, 'started')

  def test_one_succeeding_one_failing_promises(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    self.fake_waiting_time = 0.2

    for i in range(2):
      worked_file = os.path.join(instance.partition_path, 'promise_worked_%d' % i)
      lockfile = os.path.join(instance.partition_path, 'lock')
      promise=("""#!/usr/bin/env sh
touch "%(worked_file)s"
if [ ! -f %(lockfile)s ]
then
  touch "%(lockfile)s"
  exit 0
else
  exit 127
fi""" % {'worked_file': worked_file, 'lockfile': lockfile})
      instance.setPromise('promise_%s'%i,promise)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertEquals(instance.error, 1)
    self.assertNotEqual('started',instance.state)

  def test_one_succeeding_one_timing_out_promises(self):
    computer = ComputerForTest(self.software_root,self.instance_root)
    instance = computer.instance_list[0]
    instance.requested_state = 'started'
    self.fake_waiting_time = 0.2
    for i in range(2):
      worked_file = os.path.join(instance.partition_path, 'promise_worked_%d' % i)
      lockfile = os.path.join(instance.partition_path, 'lock')
      promise = ("""#!/usr/bin/env sh
touch "%(worked_file)s"
if [ ! -f %(lockfile)s ]
then
  touch "%(lockfile)s"
else
  sleep 5
fi
exit 0"""  % {'worked_file': worked_file, 'lockfile': lockfile})
      instance.setPromise('promise_%d' % i, promise)

    self.assertFalse(self.grid.processComputerPartitionList())

    self.assertEquals(instance.error, 1)
    self.assertNotEqual(instance.state,'started')
