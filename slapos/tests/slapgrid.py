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

class BasicMixin:
  def assertSortedListEqual(self, list1, list2, msg=None):
    self.assertListEqual(sorted(list1), sorted(list2), msg)

  def setUp(self):
    self._tempdir = tempfile.mkdtemp()
    logging.basicConfig(level=logging.DEBUG)
    self.setSlapgrid()

  def setSlapgrid(self, develop=False):
    self.software_root = os.path.join(self._tempdir, 'software')
    self.instance_root = os.path.join(self._tempdir, 'instance')
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

  def _create_instance(self, name=0):

    if not os.path.isdir(self.instance_root):
      os.mkdir(self.instance_root)

    partition_path = os.path.join(self.instance_root, str(name))
    os.mkdir(partition_path, 0750)
    return partition_path

  def _bootstrap(self):
    os.mkdir(self.software_root)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    return software_hash

  def setUp(self):
    self._patchHttplib()
    self._mock_sleep()
    BasicMixin.setUp(self)

  def tearDown(self):
    self._unpatchHttplib()
    self._unmock_sleep()
    BasicMixin.tearDown(self)


def _server_response (self_test, _requested_state, timestamp=None):
  def server_response(self_httplib, path, method, body, header):
    parsed_url = urlparse.urlparse(path.lstrip('/'))
    self_test.sequence.append(parsed_url.path)
    if method == 'GET':
      parsed_qs = urlparse.parse_qs(parsed_url.query)
    else:
      parsed_qs = urlparse.parse_qs(body)
    if parsed_url.path == 'getFullComputerInformation' and \
          'computer_id' in parsed_qs:
      slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
      slap_computer._software_release_list = []
      partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
                                                '0')
      sr = slapos.slap.SoftwareRelease()
      sr._software_release = 'http://sr/'
      partition._software_release_document = sr
      partition._requested_state = _requested_state
      if not timestamp == None :
        partition._parameter_dict = {'timestamp': timestamp}
      slap_computer._computer_partition_list = [partition]
      return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
    if parsed_url.path == 'availableComputerPartition' and \
          method == 'POST' and 'computer_partition_id' in parsed_qs:
      return (200, {}, '')
    if parsed_url.path == 'startedComputerPartition' and \
          method == 'POST' and 'computer_partition_id' in parsed_qs:
      self_test.assertEqual(parsed_qs['computer_partition_id'][0], '0')
      self_test.started = True
      return (200, {}, '')
    if parsed_url.path == 'stoppedComputerPartition' and \
          method == 'POST' and 'computer_partition_id' in parsed_qs:
      self_test.assertEqual(parsed_qs['computer_partition_id'][0], '0')
      self_test.stopped = True
      return (200, {}, '')
    if parsed_url.path == 'softwareInstanceError' and \
          method == 'POST' and 'computer_partition_id' in parsed_qs:
      self_test.error = True
      self_test.assertEqual(parsed_qs['computer_partition_id'][0], '0')
      return (200, {}, '')
    else:
      return (404, {}, '')

  return server_response


class TestSlapgridCPWithMaster(MasterMixin, unittest.TestCase):

  def test_nothing_to_do(self):

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        slap_computer._computer_partition_list = []
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['etc', 'var'])
    self.assertSortedListEqual(os.listdir(self.software_root), [])

  def test_one_partition(self):
    self.sequence = []
    httplib.HTTPConnection._callback = _server_response(self,
      _requested_state='stopped')

    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['worked',
      'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])

  def test_one_partition_started(self):
    self.sequence = []
    self.started = False
    httplib.HTTPConnection._callback = _server_response(self,'started')
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked &&
mkdir -p etc/run &&
echo "#!/bin/sh" > etc/run/wrapper &&
echo "while :; do echo "Working\\nWorking\\n" ; done" >> etc/run/wrapper &&
chmod 755 etc/run/wrapper
""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(partition_path), ['.0_wrapper.log',
      'worked', 'buildout.cfg', 'etc'])
    tries = 10
    wrapper_log = os.path.join(partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertTrue(self.started)


  def test_one_partition_started_stopped(self):
    self.started = True
    self.sequence = []
    httplib.HTTPConnection._callback = _server_response(self,'started')

    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
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
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(partition_path), ['.0_wrapper.log',
      'worked', 'buildout.cfg', 'etc'])
    wrapper_log = os.path.join(partition_path, '.0_wrapper.log')
    tries = 10
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    os.path.getsize(wrapper_log)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertTrue(self.started)

    self.stopped = False
    self.sequence = []
    self.setSlapgrid()
    httplib.HTTPConnection._callback = _server_response(self,'stopped')

    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(partition_path), ['.0_wrapper.log',
      '.0_wrapper.log.1', 'worked', 'buildout.cfg', 'etc'])
    tries = 10
    expected_text = 'Signal handler called with signal 15'
    while tries > 0:
      tries -= 1
      found = expected_text in open(wrapper_log, 'r').read()
      if found:
        break
      time.sleep(0.2)
    self.assertTrue(found)
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])
    self.assertTrue(self.stopped)


  def test_one_partition_stopped_started(self):
    self.stopped = False
    self.sequence = []
    httplib.HTTPConnection._callback = _server_response(self,'stopped')

    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked &&
mkdir -p etc/run &&
echo "#!/bin/sh" > etc/run/wrapper &&
echo "while :; do echo "Working\\nWorking\\n" ; done" >> etc/run/wrapper &&
chmod 755 etc/run/wrapper
""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['worked', 'etc',
      'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition'])
    self.assertTrue(self.stopped)

    self.started = False
    self.sequence = []
    httplib.HTTPConnection._callback = _server_response(self,'started')

    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition), ['.0_wrapper.log',
      'worked', 'etc', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    tries = 10
    wrapper_log = os.path.join(partition_path, '.0_wrapper.log')
    while tries > 0:
      tries -= 1
      if os.path.getsize(wrapper_log) > 0:
        break
      time.sleep(0.2)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'startedComputerPartition'])
    self.assertTrue(self.started)

class TestSlapgridCPPartitionProcessing (MasterMixin, unittest.TestCase):

  def test_partition_timestamp(self):

    self.sequence = []
    self.timestamp = str(int(time.time()))
    self.started = False
    httplib.HTTPConnection._callback = _server_response(
        self, 'stopped', self.timestamp)

    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(
        os.listdir(partition), ['.timestamp', 'worked', 'buildout.cfg'])
    self.assertSortedListEqual(
        os.listdir(self.software_root), [software_hash])
    timestamp_path = os.path.join(partition_path, '.timestamp')

    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(self.timestamp in open(timestamp_path,'r').read())
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation',
                      'availableComputerPartition',
                      'stoppedComputerPartition',
                      'getFullComputerInformation'])


  def test_partition_timestamp_develop(self):

    self.sequence = []
    self.timestamp = str(int(time.time()))
    self.started = False
    httplib.HTTPConnection._callback = _server_response(
        self, 'stopped', self.timestamp)
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(
        os.listdir(partition), ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(
        os.listdir(self.software_root), [software_hash])

    self.setSlapgrid(develop=True)
    self.assertTrue(self.grid.processComputerPartitionList())

    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())

    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition','stoppedComputerPartition',
                      'getFullComputerInformation'])

  def test_partition_old_timestamp(self):

    self.sequence = []
    self.timestamp = str(int(time.time()))
    self.started = False
    httplib.HTTPConnection._callback = _server_response(
        self,'stopped', self.timestamp)

    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition),
                               ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])

    self.setSlapgrid()
    httplib.HTTPConnection._callback = _server_response(
        self, 'stopped', str(int(self.timestamp)-1))
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation'])



  def test_partition_timestamp_new_timestamp(self):

    self.sequence = []
    self.timestamp = str(int(time.time()))
    self.started = False
    httplib.HTTPConnection._callback = _server_response(self,
                                                        'stopped',
                                                        self.timestamp)
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition),
                               ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    httplib.HTTPConnection._callback = _server_response(self,
                                                        'stopped',
                                                        str(int(self.timestamp)+1))
    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition','stoppedComputerPartition',
                      'getFullComputerInformation'])

  def test_partition_timestamp_no_timestamp(self):

    self.sequence = []
    self.timestamp = str(int(time.time()))
    self.started = False
    httplib.HTTPConnection._callback = _server_response(self,
                                                        'stopped',
                                                        self.timestamp)
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    partition_path = os.path.join(self.instance_root, '0')
    os.mkdir(partition_path, 0750)
    software_hash = slapos.grid.utils.getSoftwareUrlHash('http://sr/')
    srdir = os.path.join(self.software_root, software_hash)
    os.mkdir(srdir)
    open(os.path.join(srdir, 'template.cfg'), 'w').write(
      """[buildout]""")
    srbindir = os.path.join(srdir, 'bin')
    os.mkdir(srbindir)
    open(os.path.join(srbindir, 'buildout'), 'w').write("""#!/bin/sh
touch worked""")
    os.chmod(os.path.join(srbindir, 'buildout'), 0755)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    partition = os.path.join(self.instance_root, '0')
    self.assertSortedListEqual(os.listdir(partition),
                               ['.timestamp','worked', 'buildout.cfg'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])
    httplib.HTTPConnection._callback = _server_response(self,
                                                        'stopped')
    self.setSlapgrid()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertEqual(self.sequence,
                     ['getFullComputerInformation', 'availableComputerPartition',
                      'stoppedComputerPartition', 'getFullComputerInformation',
                      'availableComputerPartition','stoppedComputerPartition',])


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

class TestSlapgridCPWithMasterPromise(MasterMixin, unittest.TestCase):
  def test_one_failing_promise(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)
      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error = True
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.2
    self.error = False
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    fail = os.path.join(promise_path, 'fail')
    worked_file = os.path.join(instance_path, 'fail_worked')
    with open(fail, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 127""" % {'worked_file': worked_file})
    os.chmod(fail, 0777)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(self.error)
    self.assertFalse(self.started)

  def test_one_succeeding_promise(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error = True
        raise AssertionError('ComputerPartition.error was raised')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.2
    self.error = False
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'succeed')
    worked_file = os.path.join(instance_path, 'succeed_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 0""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertFalse(self.error)
    self.assertTrue(self.started)

  def test_stderr_has_been_sent(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error = True
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        # XXX: Hardcoded dropPrivileges line ignore
        self.error_log = '\n'.join([line for line in parsed_qs['error_log'][0].splitlines()
                               if 'dropPrivileges' not in line])
        # end XXX
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.5
    self.error = False
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'stderr_writer')
    worked_file = os.path.join(instance_path, 'stderr_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
echo Error 1>&2
exit 127""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertEqual(self.error_log, 'Error')
    self.assertTrue(self.error)
    self.assertFalse(self.started)


  def test_timeout_works(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)
      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error = True
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        # XXX: Hardcoded dropPrivileges line ignore
        error_log = '\n'.join([line for line in parsed_qs['error_log'][0].splitlines()
                               if 'dropPrivileges' not in line])
        # end XXX
        self.assertEqual(error_log, 'The promise %r timed out' % 'timed_out_promise')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.2
    self.error = False
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'timed_out_promise')
    worked_file = os.path.join(instance_path, 'timed_out_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
sleep 5
exit 0""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)
    self.assertFalse(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(self.error)
    self.assertFalse(self.started)

  def test_two_succeeding_promises(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error = True
        raise AssertionError('ComputerPartition.error was raised')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.2
    self.error = False
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)

    succeed = os.path.join(promise_path, 'succeed')
    worked_file = os.path.join(instance_path, 'succeed_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 0""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)

    succeed_2 = os.path.join(promise_path, 'succeed_2')
    worked_file_2 = os.path.join(instance_path, 'succeed_2_worked')
    with open(succeed_2, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
exit 0""" % {'worked_file': worked_file_2})
    os.chmod(succeed_2, 0777)

    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))
    self.assertTrue(os.path.isfile(worked_file_2))

    self.assertFalse(self.error)
    self.assertTrue(self.started)

  def test_one_succeeding_one_failing_promises(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error += 1
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.2
    self.error = 0
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)

    promises_files = []
    for i in range(2):
      promise = os.path.join(promise_path, 'promise_%d' % i)
      promises_files.append(promise)
      worked_file = os.path.join(instance_path, 'promise_worked_%d' % i)
      lockfile = os.path.join(instance_path, 'lock')
      with open(promise, 'w') as f:
        f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
if [ ! -f %(lockfile)s ] 
then
  touch "%(lockfile)s" 
  exit 0 
else 
  exit 127
fi""" % {'worked_file': worked_file, 'lockfile': lockfile})
      os.chmod(promise, 0777)
    self.assertFalse(self.grid.processComputerPartitionList())
    for file_ in promises_files:
      self.assertTrue(os.path.isfile(file_))

    self.assertEquals(self.error, 1)
    self.assertFalse(self.started)

  def test_one_succeeding_one_timing_out_promises(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getFullComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'availableComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        return (200, {}, '')
      if parsed_url.path == 'startedComputerPartition' and \
            method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        self.started = True
        return (200, {}, '')
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error += 1
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.2
    self.error = 0
    self.started = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)

    promises_files = []
    for i in range(2):
      promise = os.path.join(promise_path, 'promise_%d' % i)
      promises_files.append(promise)
      worked_file = os.path.join(instance_path, 'promise_worked_%d' % i)
      lockfile = os.path.join(instance_path, 'lock')
      with open(promise, 'w') as f:
        f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
<<<<<<< HEAD
if [ ! -f %(lockfile)s ]
then
  touch "%(lockfile)s"
else
=======
if [ ! -f %(lockfile)s ] 
then
  touch "%(lockfile)s" 
else 
>>>>>>> master
  sleep 5
fi
exit 0"""  % {'worked_file': worked_file, 'lockfile': lockfile})
      os.chmod(promise, 0777)


    self.assertFalse(self.grid.processComputerPartitionList())
    for file_ in promises_files:
      self.assertTrue(os.path.isfile(file_))

    self.assertEquals(self.error, 1)
    self.assertFalse(self.started)

  def test_slapgrid_processes_partition_after_global_timeout(self):
    """
    """
    raise NotImplementedError()

  def test_slapgrid_processes_partition_after_timeout_defined_by_software_release(self):
    """
    """
    raise NotImplementedError()
