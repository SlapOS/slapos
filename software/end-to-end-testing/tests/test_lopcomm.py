import json
import time
import slapos.testing.e2e as e2e
from websocket import create_connection

class WebsocketTestClass(e2e.EndToEndTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()

            cls.enb_instance_name = time.strftime('e2e-cb003-enb-%Y-%B-%d-%H:%M:%S')
            cls.cn_instance_name = time.strftime('e2e-cb003-core-network-%Y-%B-%d-%H:%M:%S')
            cls.sim_instance_name = time.strftime('e2e-cb003-sim-%Y-%B-%d-%H:%M:%S')
            cls.ue_instance_name = time.strftime('e2e-sb005-ue-%Y-%B-%d-%H:%M:%S')

            cls.product = "/opt/e2e/slapos/software/simpleran/software-fdd-lopcomm.cfg"
            cls.ue_product = "/opt/e2e/slapos/software/simpleran/software-fdd-lopcomm.cfg"

            # Component GUIDs and configurations
            cls.comp_enb ="COMP-3920"
            cls.comp_cn = "COMP-3920"
            cls.comp_ue = "COMP-3756"
            cls.dl_earfcn = 300

            # Retry configurations
            cls.max_retries = 10
            cls.retry_delay = 180  # seconds

            # Setup instances
            cls.setup_instances()

            cls.waitUntilGreen(cls.enb_instance_name)
            cls.waitUntilGreen(cls.cn_instance_name)

        except Exception as e:
            cls.logger.error("Error during setup: " + str(e))
            # Ensure cleanup
            cls.tearDownClass()
            raise

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
    def setup_instances(cls):
        cls.request_enb()
        cls.request_core_network()
        cls.setup_websocket_connection()

    @classmethod
    def request_enb(cls, custom_params=None):
        cls.logger.info("Request "+ cls.enb_instance_name)
        enb_parameters = {
            "bandwidth": "20 MHz",
            "n_antenna_dl": 1,
            "n_antenna_ul": 1,
            "cpri_mult": 16,
            "cell_list": {
                "RRH-B1": {
                    "cpri_rx_delay": 25.11,
                    "cpri_tx_delay": 13.77,
                    "cpri_tx_dbm": 56,
                    "ru_mac_addr": "00:0a:00:00:10:20",
                    "dl_earfcn": cls.dl_earfcn
                }
            },
            "dnsmasq": True,
            "txa0cc00_active": "ACTIVE",
            "rxa0cc00_active": "ACTIVE",
            "txa0cc00_center_frequency": 2140,
            "rxa0cc00_center_frequency_earfcn": 18300,
            "rxa0cc00_center_frequency": 1950,
            "txa0cc00_gain": -20,
            "user-authorized-key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDegkDlZaDJEoiXo5FZ5iJmYcVHyqd5G+YaWLmZ/Ae6wtY8Pp0e/+eCcARO67pwn73MAj9IELu3h5rdPuZvZx0xXWGOc3ceOQBsJh/h4eMpiBKvA5ELWVuXDIl98xgIIjiaO4QgZyw1OhpN5EB6EyUNKt/xCHuU37mZaFLbcNDW3h6JI5U5plIARY0e/dFPFywtKqCgnqhJubJh/kHcb4ZeJzQMnA33WGwVD/b+F015kHXfk4T259Z27yqMTokVjaiUnI2Wbac3e+Lc5bpecA68rlmhc6fs0bh5Geldy2Q8y8gJQUX3sihA9PjlDN+T8mNYHyk9QaCM/SQkwxB71D172nMoUcrppUZyf6JaLmB/cO0iVsIr8x2GnGT0EzL/y1hmvi1dD17E0DpgoRcjI3DxleTbUTpayT4ZHrtVnkp2Nf1LgEJmdTx0hqTb9HTqhXATTKLSETYAwIu0yWnlA9oK2MwsiPPQ/8IS5HzhN3XFEIdV+tQ7GZPVfv4sYpwt7us= root@root",
            "plmn_list": {"Australia": {"plmn": "50501"}}
        }

        if custom_params:
            enb_parameters.update(custom_params)

        json_enb_parameters = json.dumps(enb_parameters)

        cls.retry_request(cls.request, cls.product, cls.enb_instance_name,
                          filter_kw={"computer_guid": cls.comp_enb},
                          partition_parameter_kw={'_': json_enb_parameters},
                          software_type='enb')

    @classmethod
    def request_core_network(cls):
        cls.logger.info("Request "+ cls.cn_instance_name)
        core_network_parameters = json.dumps({"core_network_plmn": "50501"})
        cls.retry_request(cls.request_core_network_with_guid, core_network_parameters)

    @classmethod
    def request_core_network_with_guid(cls, core_network_parameters):
        core_network_instance = cls.request(cls.product, cls.cn_instance_name,
                                            filter_kw={"computer_guid": cls.comp_cn},
                                            partition_parameter_kw={'_': core_network_parameters},
                                            software_type='core-network')
        if core_network_instance:
            instance_infos = cls.getInstanceInfos(cls.cn_instance_name)
            cls.cn_instance_guid = instance_infos.news['instance'][0]['reference']
            cls.request_demo_sim_cards()
            return True
        return False

    @classmethod
    def request_demo_sim_cards(cls):
        cls.logger.info("Request "+ cls.sim_instance_name)
        if cls.cn_instance_guid is None:
            cls.logger.error("Core network instance GUID not set. Cannot request demo SIM cards.")
            return

        sim_card_parameters = json.dumps({
            "sim_algo": "xor",
            "imsi": "505010123456789",
            "k": "00112233445566778899aabbccddeeff",
            "imeisv": "8682430000000101",
            "impi": "505010123456789@ims.mnc505.mcc001.3gppnetwork.org",
            "impu": ["505010123456789", "tel:0600000000", "tel:600"]
        })

        cls.retry_request(cls.request, cls.product, cls.sim_instance_name,
                        partition_parameter_kw={'_': sim_card_parameters},
                        software_type='core-network',
                        filter_kw={"instance_guid": cls.cn_instance_guid},
                        shared=True, state='started')

    @classmethod
    def setup_websocket_connection(cls):
        ue_instance = cls.retry_request(cls.request_ue)
        cls.waitUntilGreen(cls.ue_instance_name)
        cls.ue_com_addr = ue_instance.get('com_addr') if ue_instance else None
        if not cls.ue_com_addr:
            cls.logger.error("Failed to obtain UE com address.")
            return

        cls.ws_url = f"ws://{cls.ue_com_addr}"
        cls.logger.info(f"Websocket URL: {cls.ws_url}")

        for attempt in range(cls.max_retries):
            try:
                cls.ws = create_connection(cls.ws_url)
                cls.logger.info("Websocket connection established.")
                break
            except Exception as e:
                cls.logger.error(f"Websocket connection attempt {attempt + 1} failed: {e}")
                if attempt < cls.max_retries - 1:
                    time.sleep(5)

    @classmethod
    def request_ue(cls):
        cls.logger.info("Request "+ cls.ue_instance_name)
        ue_parameters = json.dumps({
            "n_antenna_dl": 2,
            "n_antenna_ul": 2,
            "dl_earfcn": cls.dl_earfcn,
            "sim_algo": "xor",
            "imsi": "505010123456789",
            "k": "00112233445566778899aabbccddeeff",
            "imeisv": "8682430000000101",
            "impi": "505010123456789@ims.mnc505.mcc001.3gppnetwork.org",
            "impu": ["505010123456789", "tel:0600000000", "tel:600"]
        })

        return cls.retry_request(cls.request, cls.ue_product, cls.ue_instance_name,
                               filter_kw={"computer_guid": cls.comp_ue},
                               partition_parameter_kw={'_': ue_parameters},
                               software_type='ue-lte')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws') and cls.ws is not None:
            cls.ws.close()
        super().tearDownClass()

    def send(self, msg):
        self.ws.send(json.dumps(msg))

    def recv(self):
        return json.loads(self.ws.recv())

    def ue_get(self):
        self.send({"message": "ue_get"})
        result = self.recv()

        if 'message' not in result:
            raise ValueError(f"Unexpected response format: {result}")

        if 'ue_list' in result:
            if not result['ue_list']:
                raise ValueError(f"No UE found in response: {result}")
            return result['ue_list'][0]
        else:
            return result

    def power_on(self, ue_id):
        self.assertFalse(self.ue_get()['power_on'], "UE already powered on")
        self.send({"message": "power_on", "ue_id": ue_id})
        self.recv()

    def power_off(self, ue_id):
        self.assertTrue(self.ue_get()['power_on'], "UE already powered off")
        self.send({"message": "power_off", "ue_id": ue_id})
        self.recv()

class BBUTest(WebsocketTestClass):
    def test_ue_has_ip(self):
      result = self.recv()
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

    def test_max_rx_sample_db(self):
        pass
        # check-rx-saturated is disabled for BBU+RU
        # custom_params = {"max_rx_sample_db": -99}
        # BBUTest.request_enb(custom_params)
        # self.waitUntilPromises(BBUTest.enb_instance_name, promise_name="check-rx-saturated", expected=False)

    def test_min_rxtx_delay(self):
        custom_params = {"min_rxtx_delay": 99}
        BBUTest.request_enb(custom_params)
        self.waitUntilPromises(BBUTest.enb_instance_name, promise_name="check-baseband-latency", expected=False)
