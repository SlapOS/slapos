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
    self.software_root = os.path.join(self._tempdir, 'software')
    self.instance_root = os.path.join(self._tempdir, 'instance')
    if getattr(self, 'master_url', None) is None:
      self.master_url = 'http://127.0.0.1:0/'
    self.computer_id = 'computer'
    self.supervisord_socket = os.path.join(self._tempdir, 'supervisord.sock')
    self.supervisord_configuration_path = os.path.join(self._tempdir,
      'supervisord')
    self.usage_report_periodicity = 1
    self.buildout = None
    logging.basicConfig(level=logging.DEBUG)
    self.grid = slapgrid.Slapgrid(self.software_root, self.instance_root,
      self.master_url, self.computer_id, self.supervisord_socket,
      self.supervisord_configuration_path, self.usage_report_periodicity,
      self.buildout)

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

class TestSlapgridCPWithMaster(MasterMixin, unittest.TestCase):

  def test_nothing_to_do(self):

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
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

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
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

  def test_one_partition_started(self):

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
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

  def test_one_partition_started_stopped(self):

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
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
    last_size = os.path.getsize(wrapper_log)
    self.assertTrue('Working' in open(wrapper_log, 'r').read())
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')
    httplib.HTTPConnection._callback = server_response
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

  def test_one_partition_stopped_started(self):

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
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

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'started'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
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


  def test_one_failing_promise(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
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
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(self.error)

  def test_one_succeeding_promise(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
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

  def test_stderr_has_been_sent(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
      if parsed_url.path == 'softwareInstanceError' and \
         method == 'POST' and 'computer_partition_id' in parsed_qs:
        self.error = True
        self.assertEqual(parsed_qs['computer_partition_id'][0], '0')
        # XXX: Hardcoded dropPrivileges line ignore
        error_log = '\n'.join([line for line in parsed_qs['error_log'][0].splitlines()
                               if 'dropPrivileges' not in line])
        # end XXX
        self.assertEqual(error_log, 'Error')
        return (200, {}, '')
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    self.fake_waiting_time = 0.5
    self.error = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'stderr_writer')
    worked_file = os.path.join(instance_path, 'stderr_worked')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
touch "%(worked_file)s"
echo -n Error 1>&2
exit 127""" % {'worked_file': worked_file})
    os.chmod(succeed, 0777)
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(self.error)

  def test_timeout_works(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
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
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertTrue(os.path.isfile(worked_file))

    self.assertTrue(self.error)

  def test_two_succeeding_promises(self):

    def server_response(self_httplib, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))

      if method == 'GET':
        parsed_qs = urlparse.parse_qs(parsed_url.query)
      else:
        parsed_qs = urlparse.parse_qs(body)

      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
        slap_computer._software_release_list = []
        partition = slapos.slap.ComputerPartition(parsed_qs['computer_id'][0],
            '0')
        partition._need_modification = True
        sr = slapos.slap.SoftwareRelease()
        sr._software_release = 'http://sr/'
        partition._software_release_document = sr
        partition._requested_state = 'stopped'
        slap_computer._computer_partition_list = [partition]
        return (200, {}, xml_marshaller.xml_marshaller.dumps(slap_computer))
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

