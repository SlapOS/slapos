#!{{ python_path }}
import json
import logging
import time
import xmltodict
from logging.handlers import RotatingFileHandler
from ncclient import manager
from ncclient.xml_ import *
from ncclient.devices.default import DefaultDeviceHandler

class LopcommNetconfClient:

    def __init__(self):

        log_file = "{{ log_file }}"
        json_log_file = "{{ json_log_file }}"
        cfg_json_log_file = "{{ cfg_json_log_file }}"

        self.logger = logging.getLogger('logger')
        self.json_logger = logging.getLogger('json_logger')
        self.cfg_json_logger = logging.getLogger('cfg_json_logger')
        self.logger.setLevel(logging.DEBUG)
        self.json_logger.setLevel(logging.DEBUG)
        self.cfg_json_logger.setLevel(logging.DEBUG)

        json_handler = RotatingFileHandler(json_log_file, maxBytes=100000, backupCount=5)
        json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
        json_handler.setFormatter(json_formatter)
        self.json_logger.addHandler(json_handler)

        cfg_json_handler = RotatingFileHandler(cfg_json_log_file, maxBytes=100000, backupCount=5)
        cfg_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
        cfg_json_handler.setFormatter(cfg_json_formatter)
        self.cfg_json_logger.addHandler(cfg_json_handler)

        handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
        self.logger.addHandler(handler)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        if {{ testing }}:
            return

    def connect(self, host, port, user, password):

        if {{ testing }}:
            return

        self.address = (host, port)

        self.logger.info('Connecting to %s, user %s...' % (self.address, user))

        self.conn = manager.connect(host=host,
                               port=port,
                               username=user,
                               password=password,
                               timeout=1800,
                               device_params={
                                   'name': 'default'
                               },
                               hostkey_verify=False)

        self.logger.info('Connection to %s successful' % (self.address,))

    def subscribe(self):

        # Filter not compatible between ncclient and netconf server
        #result = self.conn.create_subscription(filter=('xpath', '/o-ran-fm:*'))
        sub = self.conn.create_subscription()
        self.logger.info('Subscription to %s successful' % (self.address,))

    def get_notification(self):

        result = None
        while result == None:
            self.logger.debug('Waiting for notification from %s...' % (self.address,))
            result = self.conn.take_notification(block=True)
            if result:
              self.logger.debug('Got new notification from %s...' % (self.address,))
              result_in_xml = result._raw
              data_dict = xmltodict.parse(result_in_xml)
              if 'alarm-notif' in data_dict['notification']:
                self.json_logger.info('', extra={'data': data_dict})
              else:
                self.cfg_json_logger.info('', extra={'data': data_dict})


    def close(self):
        # Close not compatible between ncclient and netconf server
        #self.conn.close()
        pass

if __name__ == '__main__':

    nc = LopcommNetconfClient()
    while True:
      try:
          nc.connect("2a11:9ac1:6:800a::1", 830, "oranuser", "oranpassword")
          nc.subscribe()
          while True:
            nc.get_notification()
      except Exception as e:
          nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
          nc.logger.debug(e)
          time.sleep(10)
      finally:
          nc.close()
