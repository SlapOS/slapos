#!{{ python_path }}
import logging
import time
import xmltodict
from logging.handlers import RotatingFileHandler
from ncclient import manager
from ncclient.operations import RPCError
from ncclient.xml_ import *
from ncclient.devices.default import DefaultDeviceHandler

class LopcommNetconfClient:

    def __init__(self):

        log_file = "{{ log_file }}"

        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logging.DEBUG)

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

    def edit_config(self, config_files):
        for config_file in config_files:
            with open(config_file) as f:
                config_xml = f.read()

            try:
                self.logger.info('Sending edit-config RPC request...')
                self.conn.edit_config(target='running', config=config_xml)
                self.logger.info('Edit-config RPC request sent successfully')
            except RPCError as e:
                self.logger.error('Error sending edit-config RPC request: %s' % e)

    def close(self):
        # Close not compatible between ncclient and netconf server
        #self.conn.close()
        pass

if __name__ == '__main__':
    nc = LopcommNetconfClient()
    while True:
        try:
            nc.connect("{{ netaddr.IPAddress(slap_configuration.get('tap-ipv6-gateway', '')) }}", 830, "oranuser", "oranpassword")
            nc.edit_config(["{{ CreateProcessingEle_template }}", "{{ cu_config_template }}"])
            break
        except Exception as e:
            nc.logger.debug('Got exception, waiting 10 seconds before reconnecting...')
            nc.logger.debug(e)
            time.sleep(10)
        finally:
            nc.close()
