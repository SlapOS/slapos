import unittest
import requests
from StringIO import StringIO

import SimpleHTTPServer
import SocketServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os

import time
import utils
import threading
import subprocess
import psutil

test_msg = "dummyInputSimpleIngest"
caddy_pidfile = os.environ.get('CADDY_DIR')
with open(caddy_pidfile) as f:
  caddy_pid = f.readline()

if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()

class FluentdPluginTestCase(utils.SlapOSInstanceTestCase):
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')), )

class TestServerHandler(BaseHTTPRequestHandler):
  
    posted_data = None
    all_data = []
    request_tag = ""

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write("<html><body><h1>hi!</h1></body></html>")

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself

        self._set_headers()
        self.wfile.write(post_data)

        TestServerHandler.posted_data = post_data.split(" ")[1]

        TestServerHandler.all_data.append(post_data.split(" ")[1])
        
        TestServerHandler.request_tag = find_tag(self.requestline,"=", " ")

class TestIngestion(FluentdPluginTestCase):
    
    @classmethod
    def startServer(cls):
      port=9443
      server_address = (os.environ['LOCAL_IPV4'], port)
      cls.server = HTTPServer(server_address, TestServerHandler)
      cls.thread = threading.Thread(target=cls.server.serve_forever)
      cls.thread.start()
      print("server start")
      
    @classmethod
    def stopServer(cls):
      cls.server.shutdown()
      cls.server.server_close()
      print("serever shutdown")
    
    def setUp(self):
      self.startServer()

    def tearDown(self):
      self.stopServer()
      
    def test_get_request_responds_with_200(self):
      '''
        simple get request to be sure that server is up
      '''
      print("############## TEST 1 ##############")
      url  = self.computer_partition.getConnectionParameterDict()['url']
      resp = requests.get(url)
      self.assertEqual(resp.status_code, 200)
      print (resp.status_code)

    def test_simple_ingest(self):
      
      print("############## TEST 2 ##############")
      start_fluentd_cat(self, test_msg, "tag_test_2")
      time.sleep(10)
      self.assertEqual(test_msg, TestServerHandler.posted_data)
    
    
    def test_keepAlive_on(self):
      print("############## TEST 3 ##############")
      
      caddy_process = psutil.Process(int(caddy_pid)) 
      port=9443
    
      start_fluentd_cat(self, "dummyInputDelayCheckKeepAlive", "tag_test_3")
      time.sleep(10)

      self.assertEqual(
      ['ESTABLISHED'],
      [conn.status for conn in caddy_process.connections('inet')
        if len(conn.raddr) > 1 and  conn.laddr.port == 4443])

      #for conn in caddy_process.connections('inet'):
      #  if len(conn.raddr) > 1 and  conn.laddr.port == 4443:
      #    self.assertEqual('ESTABLISHED', conn.status) #conn.status == 'ESTABLISHED' :

    def test_ingest_with_15mins_delay(self):
      '''
        sleep 15mins to test that connections doesn't break after long delay
        and data is ingested correctly after the delay.
      '''
      print("############## TEST 4 ##############")
      
      time.sleep(900)
      start_fluentd_cat(self, "dummyInputDelay", "tag_test_4")
      time.sleep(15)
      self.assertEqual("dummyInputDelay", TestServerHandler.posted_data)

    def test_ingest_while_server_breakage(self):
      '''
         stop and then start caddy again to check that
         fluentd plugin keeps message in a local buffer
         and correctly sends them when caddy is back online
      '''
      print("############## TEST 5 ##############")

      start_fluentd_cat(self, "dummyInputCaddyRestart1", "tag_test_5_1")
      time.sleep(10)

      kill_caddy(caddy_pid)
      time.sleep(10)

      start_fluentd_cat(self, "dummyInputCaddyRestart2 ", "tag_test_5_2")
      time.sleep(10)
      start_fluentd_cat(self, "dummyInputCaddyRestart3 ", "tag_test_5_3")
      time.sleep(10)
      start_fluentd_cat(self, "dummyInputCaddyRestart4 ", "tag_test_5_4")
      time.sleep(130)

      start_caddy(caddy_pid)
      time.sleep(15)

      self.assertTrue("dummyInputCaddyRestart1" in TestServerHandler.all_data)
      self.assertTrue("dummyInputCaddyRestart2" in TestServerHandler.all_data)
      self.assertTrue("dummyInputCaddyRestart3" in TestServerHandler.all_data)
      self.assertTrue("dummyInputCaddyRestart4" in TestServerHandler.all_data)

    def test_ingest_with_diff_tags(self):
      '''
        ingest data with different tags
      '''
      print("############## TEST 6 ##############")
      
      start_fluentd_cat(self, "dummyInputTags_6_1", "tag_Test_6_1")
      time.sleep(10)
      self.assertEqual("tag_Test_6_1", TestServerHandler.request_tag)
      
      start_fluentd_cat(self, "dummyInputTags_6_2", "tag_Test_6_2")
      time.sleep(10)
      self.assertEqual("tag_Test_6_2", TestServerHandler.request_tag)
      
      start_fluentd_cat(self, "dummyInputTags_6_3", "tag_Test_6_3")
      time.sleep(10)
      self.assertEqual("tag_Test_6_3", TestServerHandler.request_tag)
      
def start_fluentd_cat(self, test_msg, tag):
  """Feeds `test_msg` with `tag` to fluentd.
  """ 
  fluent_service = os.environ.get('FLUENT_SERVICE')
  proc = subprocess.Popen(
    [fluent_service + '/bin/fluent-cat',
    '--none',
     tag,
    '-p',
    '5438',
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env={"GEM_PATH": fluent_service + "/lib/ruby/gems/1.8/" })
  stdout, stderr = proc.communicate("+ " + test_msg)
  self.assertEqual(0, proc.wait())
  self.assertEqual('', stdout)
  self.assertEqual('', stderr)

def kill_caddy(caddy_pid):
    
    os.system("kill -TSTP %s" % caddy_pid)
    print("Caddy is stopped.")

def start_caddy(caddy_pid):
    
    os.system("kill -CONT %s" % caddy_pid)
    print("Caddy is restarted.")

def find_tag(s, start, end):
  return (s.split(start))[1].split(end)[0]
