import json
import hashlib
import hmac
import random
import time
import slapos.testing.e2e as e2e
from websocket import create_connection

class WebsocketTestClass(e2e.EndToEndTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()

            cls.logger.info("Setting up class")

            cls.enb_instance_name = 'e2e-ors70-enb-2'
            cls.core_network_instance_name = 'e2e-ors70-mme-1737037360'
            cls.core_network_sim_instance_name = 'e2e-ors70-sim-card-1737037360'
            cls.ue_instance_name = 'e2e-sb005-ue-tagged'
            cls.ue_cell_instance_name = 'e2e-sb005-ue-cell-tagged'
            cls.ue_ue_instance_name = 'e2e-sb005-ue-ue-tagged'

            # Retry configurations
            cls.max_retries = 1
            cls.retry_delay = 1  # seconds

            mnc  = '02'
            mcc = '001'
            plmn = mcc + mnc
            mnc = (3 - len(mnc)) * '0' + mnc

            cls.parameters = {}
            cls.parameters['enb'] = {
                  'bandwidth': '10 MHz',
                  'dl_earfcn': 38350,
                  'plmn_list': {
                    plmn: {
                      'plmn': plmn
                    }
                   },
                  'enb_drb_stats_enabled': False,
                  'xlog_forwarding_enabled': False,
                  'amarisoft_version': '2024-03-15.1727098076'
            }
            cls.parameters['core-network#sim'] = {
                  'sim_algo': 'milenage',
                  'imsi': f'{plmn}0000000001',
                  'opc': '000102030405060708090A0B0C0D0E0F',
                  'amf': '0x9001',
                  'sqn': '000000000000',
                  'k': '00112233445566778899AABBCCDDEEFF',
                  'impu': f'{plmn}0000000001',
                  'impi': f'{plmn}0000000001@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org'
            }
            cls.parameters['core-network'] = {
                   'core_network_plmn': plmn,
                   'iperf3': True,
                   'network_name': 'E2E Testing',
                   'network_short_name': 'E2E Testing',
                  'amarisoft_version': '2024-03-15.1727098076'
            }
            cls.parameters['ue'] = {
                  'amarisoft_version': '2022-12-16.1733497882'
            }
            cls.parameters['ue#cell'] = {
                  'cell_type': 'lte',
                  'cell_kind': 'ue',
                  'rf_mode': 'tdd',
                  'ru': {
                      'ru_type': 'sdr',
                      'ru_link_type': 'sdr',
                      'sdr_dev_list': [
                          0
                      ],
                      'n_antenna_dl': 2,
                      'n_antenna_ul': 2,
                      'tx_gain': 90,
                      'rx_gain': 60,
                      'txrx_active': 'ACTIVE'
                  },
                  'dl_earfcn': 38350,
                  'ul_earfcn': 38350,
                  'bandwidth': 10
            }
            cls.parameters['ue#ue'] = {
                  'ue_type': 'lte',
                  'imsi': f'{plmn}0000000001',
                  'k': '00112233445566778899AABBCCDDEEFF',
                  'sim_algo': 'milenage',
                  'opc': '000102030405060708090A0B0C0D0E0F',
                  'amf': '0x9001',
                  'sqn': '000000000000',
                  'impu': f'{plmn}0000000001',
                  'impi': f'{plmn}0000000001@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org'
            }
            for ref in cls.parameters:
              cls.update_service(ref, 'started', parameters=cls.parameters[ref], lock=True)

            cls.logger.info("Waiting 5 minutes")
            time.sleep(5 * 60)

            cls.logger.info("Waiting until instances are green")
            cls.waitUntilGreen(cls.enb_instance_name, timeout=60 * 3)
            cls.waitUntilGreen(cls.ue_instance_name)
            cls.setup_websocket_connection()

        except Exception as e:
            cls.logger.error("Error during setup: " + str(e))
            # Ensure cleanup
            cls.tearDownClass()
            raise

    @classmethod
    def setup_websocket_connection(cls):
        connection_params = cls.getInstanceInfos(cls.ue_instance_name).connection_dict
        cls.waitUntilGreen(cls.ue_instance_name)
        cls.ws_host = connection_params.get('websocket-hostname')
        cls.ws_port = connection_params.get('websocket-port')
        cls.ws_pass = connection_params.get('websocket-password')
        cls.ws_url = f'wss://{cls.ws_host}/websocket:{cls.ws_port}'

        cls.logger.info(f"Websocket URL: {cls.ws_url}")

        cls.ws = create_connection(cls.ws_url)
        cls.logger.info("Websocket connection established.")
        data = json.loads(cls.ws.recv())
        res = hmac.new(
          '{}:{}:{}'.format(data['type'], cls.ws_pass, data['name']).encode(),
          msg=data['challenge'].encode(),
          digestmod=hashlib.sha256
        ).hexdigest()
        msg = {'message': 'authenticate', 'res': res}
        cls.ws.send(json.dumps(msg))
        cls.ws.recv()
        cls.logger.info("Websocket authentication established.")

    @classmethod
    def update_service(cls, name, state, parameters=None, lock=None):
        sr_type = name.split('#')[0]
        shared = '#' in name
        name = name.replace('#', '_').replace('-', '_')
        instance_name = getattr(cls, f'{name}_instance_name')
        instance_infos = cls.getInstanceInfos(instance_name)
        if parameters:
          parameters = {'_': json.dumps(parameters)}
        else:
          parameters = {'_': json.dumps(instance_infos.parameter_dict['_'])}

        # Lock mechanism, only for non shared instances
        while lock and not shared:
          cls.logger.info(f"Waiting for lock to be released for {instance_name}...")
          lock = time.time()
          previous_lock = float(instance_infos.parameter_dict['_'].get('lock', 0))
          # If previous lock is more than 6 hours old, then we assume the previous
          # test exited without properly releasing the lock
          if (lock - previous_lock) > (3600 * 6):
            parameters = json.loads(parameters['_'])
            parameters['lock'] = lock
            parameters = {'_': json.dumps(parameters)}
            break
          # Sleep a random amount between 1 and 10 minutes to avoid multiple test
          # suites getting the lock at the same time
          time.sleep(random.randint(60, 10 * 60))
          instance_infos = cls.getInstanceInfos(instance_name)
        # Unlock
        if lock == False:
          parameters = json.loads(parameters['_'])
          parameters.pop('lock', None)
          parameters = {'_': json.dumps(parameters)}

        cls.logger.info(f"Update {instance_name}")
        args = [instance_infos.software_url, instance_name,]
        kwargs = {
                      'shared'                : shared,
                      'partition_parameter_kw': parameters,
                      'software_type'         : sr_type,
                      'state'                 : state,}
        cls.logger.info("args = {}, kwargs = {}".format(repr(args), repr(kwargs)))

        cls.retry_request(cls.request, *args, **kwargs)

    @classmethod
    def retry_request(cls, func, *args, **kwargs):
        for attempt in range(cls.max_retries):
            try:
                result = func(*args, **kwargs)
                if result:
                    return result
            except Exception as e:
                cls.logger.error(f"Error on attempt {attempt + 1}: {e}")
            if attempt < cls.max_retries - 1:
                time.sleep(cls.retry_delay)
        return None

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws') and cls.ws is not None:
            cls.logger.info("Closing websocket")
            cls.ws.close()
        cls.update_service('enb', 'stopped', lock=False)
        cls.update_service('core-network', 'stopped', lock=False)
        cls.update_service('ue', 'stopped', lock=False)
        # Don't call super().tearDownClass as we don't want to destroy requested instances

    def send(self, msg):
        self.ws.send(json.dumps(msg))
    def recv(self):
        return json.loads(self.ws.recv())

    def ue_get(self):
        self.send({'message': 'ue_get'})
        result = self.recv()

        if 'message' not in result:
            raise ValueError(f'Unexpected response format: {result}')

        if 'ue_list' in result:
            if not result['ue_list']:
                raise ValueError(f'No UE found in response: {result}')
            return result['ue_list'][0]
        else:
            return result

    def power_on(self, ue_id):
        self.assertFalse(self.ue_get()['power_on'], "UE already powered on")
        self.send({'message': 'power_on', 'ue_id': ue_id})
        self.recv()

    def power_off(self, ue_id):
        self.assertTrue(self.ue_get()['power_on'], "UE already powered off")
        self.send({'message': 'power_off', 'ue_id': ue_id})
        self.recv()

class ORSTest(WebsocketTestClass):
    def test_ue_has_ip(self):
        result = self.ue_get()
        ue_id = result['ue_id']

        try:
            self.power_on(ue_id)
            time.sleep(5)
            result = self.ue_get()
            self.assertIn('pdn_list', result, "UE didn't connect")
            self.assertIn('ipv4', result['pdn_list'][0], "UE didn't get IPv4")
            self.logger.info("UE connected with ip: " + result['pdn_list'][0]['ipv4'])
        finally:
            self.power_off(ue_id)

    # TODO: uncomment these tests
    #def test_max_rx_sample_db(self):
    #    custom_params = {}
    #    custom_params.update(self.parameters['enb'])
    #    custom_params.update({"max_rx_sample_db": -99})
    #    self.update_service('enb', 'started', custom_params)
    #    self.waitUntilPromises(ORSTest.enb_instance_name, promise_name="check-rx-saturated", expected=False)

    #def test_min_rxtx_delay(self):
    #    # Fixed by 9798ef1e, change `expected` to False when released
    #    custom_params = {}
    #    custom_params.update(self.parameters['enb'])
    #    custom_params.update({"min_rxtx_delay": 99})
    #    self.update_service('enb', 'started', custom_params)
    #    self.waitUntilPromises(ORSTest.enb_instance_name, promise_name="check-baseband-latency", expected=True)
