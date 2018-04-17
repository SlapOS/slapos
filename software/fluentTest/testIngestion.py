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

import threading
import time


test_msg = "dummyInputPassedByFluentCAT"
url = "http://$${caddy-configuration:local_ip}:4443"

posted_data = None

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
        global message_distributor
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
     
        self._set_headers()
        self.wfile.write(post_data)
        
        global posted_data
        posted_data = post_data
        print("post data from do_POST")
        print posted_data
     
class TestPost(unittest.TestCase):
  
    posted_data = ""
  
    def test_1_get(self):
      print("############## TEST 1 ##############")
      resp = requests.get(url)
      self.assertEqual(resp.status_code, 200)
      print (resp.status_code)
    

    def test_2_ingest(self):
      print("############## TEST 2 ##############")
      start_fluentd_cat(test_msg)
      time.sleep(15)
      if posted_data:
        print(posted_data)
        self.assertEqual(test_msg, posted_data.split(" ")[1])
        print("IN IF")
      else:
        self.assertEqual(test_msg, posted_data)
        print("IN ELSE")
    
    def test_3_keepAlive_on(self):
      print("############## TEST 3 ##############")
      s = requests.session()
      print("check connection type ")
      print(s.headers['Connection'])
      self.assertEqual('keep-alive', s.headers['Connection'])
      
      
    def test_4_delay_15_mins(self):
      print("############## TEST 4 ##############")
      time.sleep(900)
      start_fluentd_cat("otherDummyMsgForFluentCat")
      time.sleep(15)
      if posted_data:
        print(posted_data)
        self.assertEqual("otherDummyMsgForFluentCat", posted_data.split(" ")[1])
      else:
        self.assertEqual(test_msg, posted_data)     
      

def start_fluentd_cat(test_msg):
    
    os.environ["GEM_PATH"] ="$${fluentd-service:path}/lib/ruby/gems/1.8/"
    
    fluentd_cat_exec_comand = '$${fluentd-service:path}/bin/fluent-cat --none wendelin_out'
    os.system("echo + " + test_msg + " | " + fluentd_cat_exec_comand)

def main():
  
   # start_fluentd_cat()
    
    port=9443
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, TestServerHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    print 'Starting http...'
    #httpd.serve_forever()
    
  #  time.sleep(15)

    stream = StringIO()
    runner = unittest.TextTestRunner(verbosity=2, stream=stream)
    result = runner.run(unittest.makeSuite(TestPost))
 
    
    print 'Tests run ', result.testsRun
    print 'Errors ', result.errors
    print "Failures ", result.failures
    stream.seek(0)
    print 'Test output\n', stream.read() 
    
    time.sleep(30)
    httpd.shutdown()
    print(posted_data)
    
    #with open("$${directory:log}/fluent_new.log", 'r') as f:
    #  log = f.read()
    #print(s)
    
    return result.testsRun, result.errors, result.failures, stream.getvalue()

if __name__ == "__main__":
  
    main()