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

class Server(BaseHTTPRequestHandler):
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
     # print(post_data)
        self._set_headers()
        self.wfile.write(post_data)

url = "http://$${caddy-configuration:local_ip}:4443"


class TestPost(unittest.TestCase):
  
    def test_get(self):
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)
        print (resp.status_code)
    
    
    def test_post(self):
        
        start_fluentd_cat()
      
        var_name_request = 'var1'
        value_request = test_mssg
        req = requests.post(url, data={var_name_request: value_request})
        var_name_response = req.text.split('=')[0]
        value_response = req.text.split('=')[1]
        self.assertEqual(var_name_request, var_name_response)
        self.assertEqual(value_request, value_response)
        
    #def test_ingest(self):
    #    var_name_request = 'var1'
    #    value_request = test_mssg
    #    # stex petqa fluentd kancvi 
    #    req = requests.post('http://10.0.46.242:4443',data={var_name_request: value_request})
    #    var_name_response = req.text.split('=')[0]
    #    value_response = req.text.split('=')[1]
    #    self.assertEqual(var_name_request, var_name_response)
    #    self.assertEqual(value_request, value_response)

test_mssg = "testtesttesttesttesttesttest"

def start_fluentd_cat():
    
    os.environ["GEM_PATH"] ="$${fluentd-service:path}/lib/ruby/gems/1.8/"
    
    fluentd_exec_comand = '$${fluentd-service:path}/bin/fluent-cat --none wendelin_out'
    os.system("echo + " + test_mssg + " | " + fluentd_exec_comand)

def main():
     #  start_fluentd_cat()
  #  thread = threading.Thread(target=start_fluentd_cat())
  #  thread.start()
  
    server_class=HTTPServer
    handler_class=Server
    port=9443
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    print 'Starting http...'
    #httpd.serve_forever()
  
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream)
    result = runner.run(unittest.makeSuite(TestPost))
 
    
    #print 'Tests run ', result.testsRun
    #print 'Errors ', result.errors
    #print "Failures ", result.failures
    stream.seek(0)
    #print 'Test output\n', stream.read() 
    
    time.sleep(60)
    
    httpd.shutdown()
    return result.testsRun, result.errors, result.failures, stream.read()
    
    
  
if __name__ == "__main__":
  
    main()