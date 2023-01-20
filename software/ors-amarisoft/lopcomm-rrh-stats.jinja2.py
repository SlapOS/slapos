#!{{ python_path }}

import json
import logging
import time
from logging.handlers import RotatingFileHandler
from ncclient import manager
from ncclient.xml_ import *
from ncclient.devices.default import DefaultDeviceHandler

class LopcommNetconfClient:

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
  
    def connect(host, port, user, password):

        if {{ testing }}:
            return

        conn = manager.connect(host=host,
                               port=port,
                               username=user,
                               password=password,
                               timeout=1800,
                               device_params={
                                   'name': 'huawei'
                               },
                               hostkey_verify=False)

        #result = conn.create_subscription(filter=('xpath', '/o-ran-fm:*'))
        sub = conn.create_subscription()
        result = None
        while result == None:
            result = conn.take_notification(block=True, timeout=60)
            print(result)
        import pdb; pdb.set_trace()
        #self.logger.info('', extra={'data': r})

if __name__ == '__main__':
    #LOG_FORMAT = '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s'
    #logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=LOG_FORMAT)
    #logging.getLogger().setLevel(logging.DEBUG)

    connect("192.168.0.210", 830, "oranuser", "oranpassword")

    nc = LopcommNetconfClient()
    while True:
      try:
          nc.connect()
          time.sleep(10)
      except Exception as e:
          nc.logger.debug(e)
      finally:
          nc.close()
