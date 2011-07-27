from slapos.grid import slapgrid
import os
import shutil
import tempfile
import unittest
import socket

class BasicMixin:
  def setUp(self):
    self._tempdir = tempfile.mkdtemp()
    self.software_root = os.path.join(self._tempdir, 'software')
    self.instance_root = os.path.join(self._tempdir, 'instance')
    self.master_url = 'http://127.0.0.1:0/'
    self.computer_id = 'computer'
    self.supervisord_socket = os.path.join(self._tempdir, 'supervisord.sock')
    self.supervisord_configuration_path = os.path.join(self._tempdir,
      'supervisord')
    self.usage_report_periodicity = 1
    self.buildout = None
    self.grid = slapgrid.Slapgrid(self.software_root, self.instance_root,
      self.master_url, self.computer_id, self.supervisord_socket,
      self.supervisord_configuration_path, self.usage_report_periodicity,
      self.buildout)

  def tearDown(self):
    shutil.rmtree(self._tempdir)

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
  _master_port = 45678
  _master_host = '127.0.0.1'
  def startMaster(self):
    self._master_dir = tempfile.mkdtemp()

  def stopMaster(self):
    shutil.rmtree(self._master_dir)

  def setUp(self):
    BasicMixin.setUp(self)
    self.startMaster()
    self.master_url = 'http://%s:%s' % (self._master_host, self._master_port)
    # prepare master

  def tearDown(self):
    self.stopMaster()
    BasicMixin.tearDown(self)

class TestSlapgridCPWithMaster(MasterMixin, unittest.TestCase):
  def test_nothing_to_do(self):
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    self.grid.processComputerPartitionList()
