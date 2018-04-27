#!${buildout:directory}/bin/${eggs:interpreter}
# BEWARE: This file is operated by slapgrid
# BEWARE: It will be overwritten automatically

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

test_msg = "dummyInputSimpleIngest"
#url = "http://$${caddy-configuration:local_ip}:8443"

url = "http://" + os.environ.get('LOCAL_IPV4') + ":4443"
#caddy_pidfile = "$${directory:etc}/caddy_pidfile"
caddy_pidfile = os.environ.get('CADDY_DIR')
posted_data = None
all_data = []
request_tag = ""

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

        global posted_data
        posted_data = post_data
        print("post data from do_POST")
        print(posted_data)
        global all_data
        all_data.append(post_data.split(" ")[1])
        
        global request_tag
        request_tag = find_tag(self.requestline,"=", " ")

class TestIngestion(FluentdPluginTestCase):

    @classmethod
    def startServer(cls):
      port=9443
      server_address = (os.environ.get('LOCAL_IPV4'), port)
      cls.server = HTTPServer(server_address, TestServerHandler)
      cls.thread = threading.Thread(target=cls.server.serve_forever)
      cls.thread.start()
      time.sleep(10)
      print("server start")
      

    @classmethod
    def stopServer(cls):
      cls.server.shutdown()
      cls.server.server_close()
      print("serever shutdown")
      time.sleep(10)
    
  #  def setUp(self):
  #    self.startServer()

  #  def tearDown(self):
  #    #self.stopServer()
   #   time.sleep(10)

    def test_1_get(self):
      
      self.startServer()
      time.sleep(10)
      print("start server")
      
      print("############## TEST 1 ##############")
      resp = requests.get(url)
      self.assertEqual(resp.status_code, 200)
      print (resp.status_code)

    def test_2_ingest(self):
      
      time.sleep(10)
      print("############## TEST 2 ##############")
      start_fluentd_cat(test_msg, "tag_test_2")
      time.sleep(10)
      print("posted data from test 2")
      print(posted_data)
      if posted_data:
        self.assertEqual(test_msg, posted_data.split(" ")[1])
      else:
        self.assertEqual(test_msg, posted_data)
      time.sleep(10)
      

    def test_3_keepAlive_on(self):
      print("############## TEST 3 ##############")
      s = requests.session()
      print("check connection type ")
      print(s.headers['Connection'])
      self.assertEqual('keep-alive', s.headers['Connection'])

    def test_4_delay_15_mins(self):
      print("############## TEST 4 ##############")
      # sleep 15mins to test that connections doesn't break after long delay
      # and data is ingested correctly after the delay.
      time.sleep(900)
      start_fluentd_cat("dummyInputDelay", "tag_test_4")
      time.sleep(15)
      self.assertEqual("dummyInputDelay", posted_data.split(" ")[1])

    def test_5_caddy_restart(self):
      print("############## TEST 5 ##############")

      with open(caddy_pidfile) as f:
        caddy_pid = f.readline()

      time.sleep(10)
      start_fluentd_cat("dummyInputCaddyRestart1", "tag_test_5_1")
      time.sleep(10)

      kill_caddy(caddy_pid)
      time.sleep(10)

      start_fluentd_cat("dummyInputCaddyRestart2 ", "tag_test_5_2")
      time.sleep(10)
      start_fluentd_cat("dummyInputCaddyRestart3 ", "tag_test_5_3")
      time.sleep(10)
      start_fluentd_cat("dummyInputCaddyRestart4 ", "tag_test_5_4")
      time.sleep(130)

      start_caddy(caddy_pid)
      time.sleep(15)

      self.assertTrue("dummyInputCaddyRestart1" in all_data)
      self.assertTrue("dummyInputCaddyRestart2" in all_data)
      self.assertTrue("dummyInputCaddyRestart3" in all_data)
      self.assertTrue("dummyInputCaddyRestart4" in all_data)

    def test_6_check_diff_tags(self):
      print("############## TEST 6 ##############")
      
      start_fluentd_cat("dummyInputTags_6_1", "test_Tag_6_1")
      time.sleep(2)
      self.assertEqual("test_Tag_6_1", request_tag)
      
      start_fluentd_cat("dummyInputTags_6_2", "test_Tag_6_2")
      time.sleep(2)
      self.assertEqual("test_Tag_6_2", request_tag)
      
      start_fluentd_cat("dummyInputTags_6_3", "test_Tag_6_3")
      time.sleep(2)
      self.assertEqual("test_Tag_6_3", request_tag)
      self.stopServer()
      time.sleep(10)
    
def start_fluentd_cat(test_msg, tag):

    fluent_service = os.environ.get('FLUENT_SERVICE')
    os.environ["GEM_PATH"] = fluent_service + "/lib/ruby/gems/1.8/"
    fluentd_cat_exec_comand = fluent_service + '/bin/fluent-cat --none ' + tag + " -p 5438 "
    os.system("echo + " + test_msg + " | " + fluentd_cat_exec_comand)
    print("Fluent-cat path")
    print(fluentd_cat_exec_comand)

def kill_caddy(caddy_pid):
    
    os.system("kill -TSTP %s" % caddy_pid)
    print("Caddy is stopped.")

def start_caddy(caddy_pid):
    
    os.system("kill -CONT %s" % caddy_pid)
    print("Caddy is restarted.")

def find_tag(s, start, end):
  return (s.split(start))[1].split(end)[0]
