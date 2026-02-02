#!{{ python_path }}
import json
import hashlib
import hmac
import logging
from logging.handlers import RotatingFileHandler
import time
from websocket import create_connection

class enbWebSocket:

    def __init__(self):

        log_file = "{{ log_file }}"

        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(log_file, maxBytes=30000, backupCount=2)
        formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.ws_url = "{{ ws_url }}"
        self.ws = create_connection(self.ws_url)

        # Password authentication
        if {{ enable_password }}:
          self.ws_password = "{{ ws_password }}"
          data = json.loads(self.ws.recv())
          res = hmac.new(
            "{}:{}:{}".format(data['type'], self.ws_password, data['name']).encode(),
            msg=data['challenge'].encode(),
            digestmod=hashlib.sha256
          ).hexdigest()
          msg = {"message": "authenticate", "res": res}
          self.ws.send(json.dumps(msg))
          self.ws.recv()

    def close(self):
        self.ws.close()

    def send(self, msg):
        self.ws.send(json.dumps(msg))
    def recv(self, message_type=None, key=None):
        for i in range(1,10):
            r = json.loads(self.ws.recv())
            if message_type and r['message'] == message_type:
                return r
            if key and key in r:
                return r
            if not key and not message_type:
                return r

    def stats(self):
        self.send({
            "message": "stats",
            "samples": True,
            "rf": True
        })
        r = self.recv(message_type='stats')
        self.send({
            "message": "rf",
            "rf_info": True
        })
        r.update(self.recv(message_type='rf'))
        self.send({
            "message": "s1",
        })
        r.update(self.recv(key="s1_list"))
        self.send({
            "message": "ng",
        })
        r.update(self.recv(key="ng_list"))
        self.logger.info('Amarisoft Stats', extra={'data': json.dumps(r)})

if __name__ == '__main__':
    ws = enbWebSocket()
    try:
        while True:
            ws.stats()
            time.sleep({{ stats_period }})
    finally:
        ws.close()
