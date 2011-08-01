from slapos.grid import slapgrid
import flask
import multiprocessing
import os
import shutil
import signal
import slapos.slap.slap
import socket
import tempfile
import unittest
import xml_marshaller

app = flask.Flask(__name__)

class BasicMixin:
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

def _run_server(host, port):
  global app
  app.run(host=host, port=port, use_reloader=False, debug=True)

class MasterMixin(BasicMixin):
  _master_port = 45678
  _master_host = '127.0.0.1'

  def startMaster(self):
    self.process = multiprocessing.Process(target=_run_server,
      args=(self._master_host, self._master_port))
    self.process.start()
    self.master_url = 'http://%s:%s/' % (self._master_host, self._master_port)

  def stopMaster(self):
    self.process.terminate()
    self.process.join()

  def setUp(self):
    # prepare master
    self.startMaster()
    BasicMixin.setUp(self)

  def tearDown(self):
    self.stopMaster()
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
  @app.route('/getComputerInformation', methods=['GET'])
  def getComputerInformation():
    computer_id = flask.request.args['computer_id']
    slap_computer = slapos.slap.Computer(computer_id)
    slap_computer._software_release_list = []
    slap_computer._computer_partition_list = []
    return xml_marshaller.xml_marshaller.dumps(slap_computer)

  def test_nothing_to_do(self):
    os.mkdir(self.software_root)
    os.mkdir(self.instance_root)
    self.assertTrue(self.grid.processComputerPartitionList())
