import time
import logging
import json
import xmltodict
from logging.handlers import RotatingFileHandler
from ncclient import manager
from ncclient.operations import RPCError
from ncclient.xml_ import *
from ncclient.devices.default import DefaultDeviceHandler

class LopcommNetconfClient:

    def __init__(self, log_file, json_log_file=None, cfg_json_log_file=None, supervision_json_log_file=None, ncsession_json_log_file=None, software_json_log_file=None, software_reply_json_log_file=None, supervision_reply_json_log_file=None, testing=False):

        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
        self.logger.addHandler(handler)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        if json_log_file:
            self.json_logger = logging.getLogger('json_logger')
            self.json_logger.setLevel(logging.DEBUG)
            json_handler = RotatingFileHandler(json_log_file, maxBytes=100000, backupCount=5)
            json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            json_handler.setFormatter(json_formatter)
            self.json_logger.addHandler(json_handler)

            self.cfg_json_logger = logging.getLogger('cfg_json_logger')
            self.cfg_json_logger.setLevel(logging.DEBUG)
            cfg_json_handler = RotatingFileHandler(cfg_json_log_file, maxBytes=100000, backupCount=5)
            cfg_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            cfg_json_handler.setFormatter(cfg_json_formatter)
            self.cfg_json_logger.addHandler(cfg_json_handler)

            self.supervision_json_logger = logging.getLogger('supervision_json_logger')
            self.supervision_json_logger.setLevel(logging.DEBUG)
            supervision_json_handler = RotatingFileHandler(supervision_json_log_file, maxBytes=100000, backupCount=5)
            supervision_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            supervision_json_handler.setFormatter(supervision_json_formatter)
            self.supervision_json_logger.addHandler(supervision_json_handler)

            self.ncsession_json_logger = logging.getLogger('ncsession_json_logger')
            self.ncsession_json_logger.setLevel(logging.DEBUG)
            ncsession_json_handler = RotatingFileHandler(ncsession_json_log_file, maxBytes=100000, backupCount=5)
            ncsession_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            ncsession_json_handler.setFormatter(ncsession_json_formatter)
            self.ncsession_json_logger.addHandler(ncsession_json_handler)

            self.software_json_logger = logging.getLogger('software_json_logger')
            self.software_json_logger.setLevel(logging.DEBUG)
            software_json_handler = RotatingFileHandler(software_json_log_file, maxBytes=100000, backupCount=5)
            software_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            software_json_handler.setFormatter(software_json_formatter)
            self.software_json_logger.addHandler(software_json_handler)

        else:
            self.json_logger = None
            self.cfg_json_logger = None
            self.supervision_json_logger = None
            self.ncsession_json_logger = None
            self.software_json_logger = None

        if supervision_reply_json_log_file:
            self.supervision_reply_json_logger = logging.getLogger('supervision_reply_json_logger')
            self.supervision_reply_json_logger.setLevel(logging.DEBUG)
            supervision_reply_json_handler = RotatingFileHandler(supervision_reply_json_log_file, maxBytes=100000, backupCount=5)
            supervision_reply_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            supervision_reply_json_handler.setFormatter(supervision_reply_json_formatter)
            self.supervision_reply_json_logger.addHandler(supervision_reply_json_handler)
        else:
            self.supervision_reply_json_logger = None

        if software_reply_json_log_file:
            self.software_reply_json_logger = logging.getLogger('software_reply_json_logger')
            self.software_reply_json_logger.setLevel(logging.DEBUG)
            software_reply_json_handler = RotatingFileHandler(software_reply_json_log_file, maxBytes=100000, backupCount=5)
            software_reply_json_formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s", "data": %(data)s}')
            software_reply_json_handler.setFormatter(software_reply_json_formatter)
            self.software_reply_json_logger.addHandler(software_reply_json_handler)
        else:
            self.software_reply_json_logger = None

        if testing:
            return

    def connect(self, host, port, user, password):
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
        sub = self.conn.create_subscription()
        self.logger.info('Subscription to %s successful' % (self.address,))
    def get_notification(self):
        self.logger.debug('Waiting for notification from %s...' % (self.address,))
        result = self.conn.take_notification(block=True, timeout=120)
        if result:
          self.logger.debug('Got new notification from %s...' % (self.address,))
          result_in_xml = result._raw
          data_dict = xmltodict.parse(result_in_xml)
          if 'alarm-notif' in data_dict['notification']:
            self.json_logger.info('', extra={'data': json.dumps(data_dict)})
          elif 'supervision-notification' in data_dict['notification']:
            self.supervision_json_logger.info('', extra={'data': json.dumps(data_dict)})
          elif 'netconf-session-start' in data_dict['notification'] or 'netconf-session-end' in data_dict['notification']:
            self.ncsession_json_logger.info('', extra={'data': json.dumps(data_dict)})
          elif any(event in data_dict['notification'] for event in ['install-event', 'activation-event', 'download-event']):
              self.software_json_logger.info('', extra={'data': json.dumps(data_dict)})
          else:
            self.cfg_json_logger.info('', extra={'data': json.dumps(data_dict)})
        else:
            raise TimeoutError
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

    def custom_rpc_request(self, rpc_xml):
        try:
            self.logger.info('Sending custom RPC request...')
            response = self.conn.dispatch(to_ele(rpc_xml))
            if response.ok:
                self.logger.info('Custom RPC request sent successfully')
                return response.xml
            else:
                self.logger.error('Error sending custom RPC request: %s' % response.error)
        except RPCError as e:
            self.logger.error('Error sending custom RPC request: %s' % e)

    def reset_device(self):
        self.logger.info('Resetting...')
        reset_rpc_xml = """
            <reset xmlns="urn:o-ran:operations:1.0">
            </reset>
        """
        reset_reply_xml = self.custom_rpc_request(reset_rpc_xml)
        if reset_reply_xml:
            reset_data = xmltodict.parse(reset_reply_xml)
            if self.software_reply_json_logger:
              self.software_reply_json_logger.info('', extra={'data': json.dumps(reset_data)})
        self.logger.info('Wait 60 second then reboot!')
        time.sleep(60)

    def get_inventory(self):
        self.logger.info('Fetching software inventory...')
        inventory_rpc_xml = """
            <get xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                <filter type="subtree">
                    <software-inventory xmlns="urn:o-ran:software-management:1.0" />
                </filter>
            </get>
        """
        inventory_reply_xml = self.custom_rpc_request(inventory_rpc_xml)
        if inventory_reply_xml:
            self.logger.info('Finish fetching software inventory.')
            inventory_data = xmltodict.parse(inventory_reply_xml)
            self.software_reply_json_logger.info('', extra={'data': json.dumps(inventory_data)})

        nonrunning_slot_name = None
        running_slot_name = None
        active_nonrunning_slot_name = None
        nonrunning_slot_name_build_version = None
        running_slot_name_build_version = None

        software_slots = inventory_data['nc:rpc-reply']['data']['software-inventory']['software-slot']
        for slot in software_slots:
            if slot['running'] == 'false':
                nonrunning_slot_name = slot['name']
                nonrunning_slot_name_build_version = slot['build-version']

            if slot['running'] == 'true':
                running_slot_name = slot['name']
                running_slot_name_build_version = slot['build-version']
            elif slot['active'] == 'true' and slot['running'] == 'false':
                active_nonrunning_slot_name = slot['name']

        return {
            "nonrunning_slot_name": nonrunning_slot_name,
            "running_slot_name": running_slot_name,
            "active_nonrunning_slot_name": active_nonrunning_slot_name,
            "nonrunning_slot_name_build_version": nonrunning_slot_name_build_version,
            "running_slot_name_build_version": running_slot_name_build_version
        }

    def close(self):
        # Close not compatible between ncclient and netconf server
        #self.conn.close()
        pass
