from slapos.grid import slapgrid
import httplib
import logging
import os
import shutil
import signal
import slapos.slap.slap
import socket
import tempfile
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
    BasicMixin.setUp(self)

  def tearDown(self):
    self._unpatchHttplib()
    # XXX: Hardcoded pid, as it is not configurable in slapos
    svc = os.path.join(self.instance_root, 'var', 'run', 'supervisord.pid')
    if os.path.exists(svc):
      try:
        pid = int(open(svc).read().strip())
      except ValueError:
        pass
      else:
        os.kill(pid, signal.SIGTERM)
    BasicMixin.tearDown(self)

class TestSlapgridCPWithMaster(MasterMixin, unittest.TestCase):

  def test_nothing_to_do(self):

    def server_response(self, path, method, body, header):
      parsed_url = urlparse.urlparse(path.lstrip('/'))
      parsed_qs = urlparse.parse_qs(parsed_url.query)
      if parsed_url.path == 'getComputerInformation' and \
         'computer_id' in parsed_qs:
        slap_computer = slapos.slap.Computer(parsed_qs['computer_id'][0])
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
      else:
        return (404, {}, '')

    httplib.HTTPConnection._callback = server_response
    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()
    self.assertTrue(self.grid.processComputerPartitionList())
    self.assertSortedListEqual(os.listdir(self.instance_root), ['0', 'etc',
      'var'])
    self.assertSortedListEqual(os.listdir(self.software_root),
      [software_hash])

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
    self.error = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    fail = os.path.join(promise_path, 'fail')
    with open(fail, 'w') as f:
      f.write("""#!/usr/bin/env sh
exit 127""")
    os.chmod(fail, 0777)
    self.assertTrue(self.grid.processComputerPartitionList())

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
    self.error = False

    instance_path = self._create_instance('0')
    software_hash = self._bootstrap()

    promise_path = os.path.join(instance_path, 'etc', 'promise')
    os.makedirs(promise_path)
    succeed = os.path.join(promise_path, 'succeed')
    with open(succeed, 'w') as f:
      f.write("""#!/usr/bin/env sh
exit 0""")
    os.chmod(succeed, 0777)
    self.assertTrue(self.grid.processComputerPartitionList())

    self.assertFalse(self.error)
