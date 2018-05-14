from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import time
import threading
import os

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
     #   global all_data
    #    all_data.append(post_data.split(" ")[1])
        
    #    global request_tag
    #    request_tag = find_tag(self.requestline,"=", " ")


def run():

  port=9443
  #server_address = ('0.0.0.0', port)
  server_address = ("10.0.46.242", port)
  server = HTTPServer(server_address, TestServerHandler)
  thread = threading.Thread(target=server.serve_forever)
  thread.start()
  print("start server")
  
  time.sleep(60)
  server.shutdown()
  server.server_close()
  print("stop server")


if __name__ == "__main__":
    run()        