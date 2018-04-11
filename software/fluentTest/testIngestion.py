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

message_distributor = None
test_msg = "testtesttesttesttesttesttest"


class MessageProxy:
  
  def __init__(self):
    self.callback = None
    
  def subscribe(self, callback):
    self.callback = callback
    
  def send(self, message):
    self.callback(message)


class TestServerHandler(BaseHTTPRequestHandler):
  
    #def __init__(self):
    #    self.forwarding_callback = None
    #    
    #def setForwardingCallback(callback):
    #    self.forwarding_callback = callback
  
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
     # print(post_data)
        self._set_headers()
        self.wfile.write(post_data)
        #if self.forwarding_callback:
        #  self.forwarding_callback(post_data)
        message_distributor.send(post_data)

url = "http://$${caddy-configuration:local_ip}:4443"


class TestPost(unittest.TestCase):
  
    def test_get(self):
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)
        print (resp.status_code)
    
    
    def test_post(self):
        var_name_request = 'var1'
        value_request = "simple POST test message"
        req = requests.post(url, data={var_name_request: value_request})
        var_name_response = req.text.split('=')[0]
        value_response = req.text.split('=')[1]
        self.assertEqual(var_name_request, var_name_response)
        self.assertEqual(value_request, value_response)
        
    def test_ingest(self):
        global message_distributor
        
        def my_callback(message):
          print("it worked with: " + message)
          self.assertEqual(test_msg, message)
        
        message_distributor.subscribe(my_callback)
        start_fluentd_cat()
        

def start_fluentd_cat():
    
    os.environ["GEM_PATH"] ="$${fluentd-service:path}/lib/ruby/gems/1.8/"
    
    fluentd_exec_comand = '$${fluentd-service:path}/bin/fluent-cat --none wendelin_out'
    os.system("echo + " + test_msg + " | " + fluentd_exec_comand)

def main():
  
    global message_distributor
    message_distributor = MessageProxy()

    port=9443
    server_address = ('', port)
    httpd = HTTPServer(server_address, TestServerHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    print 'Starting http...'
    #httpd.serve_forever()
  
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream)
    result = runner.run(unittest.makeSuite(TestPost))
 
    
  #  print 'Tests run ', result.testsRun
  #  print 'Errors ', result.errors
  #  print "Failures ", result.failures
    stream.seek(0)
  #  print 'Test output\n', stream.read() 
    
    time.sleep(10)
    httpd.shutdown()
    
    return result.testsRun, result.errors, result.failures, stream.read()
    
    
  
if __name__ == "__main__":
  
    main()