#!{{ python_path }}
import json
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

        if {{ testing }}:
            return

        self.ws_url = "ws://127.0.1.2:9001"
        self.ws = create_connection(self.ws_url)

    def close(self):
        if {{ testing }}:
            return
        self.ws.close()

    def send(self, msg):
        self.ws.send(json.dumps(msg))
    def recv(self, message_type):
        for i in range(1,20):
            r = json.loads(self.ws.recv())
            if r['message'] == message_type:
                return r

    def stats(self):
        if {{ testing }}:
            from random import randint
            nrx = {{ iru_dict.values() | sum(attribute='_.n_antenna_ul') }}
            rxv = [{'sat': 0, 'max': randint(-500,-100) / 10.0}  for _ in range(nrx)]
            r = {
                'message': 'stats',
                'samples': {'rx': rxv}
            }
        else:
            self.send({
                "message": "stats",
                "samples": True,
                "rf": True
            })
            r = self.recv('stats')
        self.logger.info('Samples stats', extra={'data': json.dumps(r)})

if __name__ == '__main__':
    ws = enbWebSocket()
    try:
        while True:
            ws.stats()
            time.sleep({{ stats_period }})
    finally:
        ws.close()
