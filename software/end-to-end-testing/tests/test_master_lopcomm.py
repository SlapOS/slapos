import json
import time
import socket
from datetime import datetime, timedelta
from websocket import create_connection
import slapos.testing.e2e as e2e


class WebsocketTestClass(e2e.EndToEndTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()

            # Dynamically named instances for different runs
            cls.set_instance_names()

            cls.product = "https://lab.nexedi.com/nexedi/slapos/-/raw/master/software/ors-amarisoft/software.cfg"
            cls.setup_guids_and_configs()

            # Setup instances
            cls.setup_instances()
            cls.waitUntilGreen(cls.enb_instance_name)
            cls.waitUntilGreen(cls.cn_instance_name)

        except Exception as e:
            cls.logger.error("Error during setup: %s", str(e))
            cls.tearDownClass()
            raise

    @classmethod
    def set_instance_names(cls):
        current_time = time.strftime('%Y-%B-%d-%H:%M:%S')
        ors_branch = 'master'
        base_names = ['enb', 'eru1', 'ecell1',
                      'cn', 'sim', 'ue', 'ucell1', 'usim']
        for name in base_names:
            setattr(cls, f"{name}_instance_name",
                    f"E2E-{ors_branch}-{name}-{current_time}")

    @classmethod
    def setup_guids_and_configs(cls):
        cls.comp_enb = "COMP-3920"
        cls.comp_cn = "COMP-3920"
        cls.comp_ue = "COMP-3756"
        cls.dl_earfcn = 300
        cls.max_retries = 10
        cls.retry_delay = 180

    @classmethod
    def setup_instances(cls):
        cls.request_core_network()
        cls.wait_for_attribute('cn_ipv6')
        cls.request_enb()
        cls.request_ue()

    @classmethod
    def retry_request(cls, func, *args, **kwargs):
        for attempt in range(cls.max_retries):
            try:
                result = func(*args, **kwargs)
                if result:
                    return result
                cls.logger.info(
                    f"Attempt {attempt + 1}: Received empty or invalid result, retrying...")
            except Exception as e:
                cls.logger.error("Error on attempt %d: %s", attempt + 1, e)
            if attempt < cls.max_retries - 1:
                cls.logger.info("Retrying...")
                time.sleep(cls.retry_delay)
        cls.logger.warning("All retry attempts failed.")
        return None

    @classmethod
    def wait_for_attribute(cls, attr_name, timeout=3600):
        start_time = time.time()
        while not hasattr(cls, attr_name) or getattr(cls, attr_name) is None:
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Timeout waiting for attribute '{attr_name}' to become available.")
            time.sleep(cls.retry_delay)
        cls.logger.info(f"Attribute '{attr_name}' is now available.")

    # Request ENB/RU/Cell
    @classmethod
    def request_enb(cls, custom_params=None):
        cls.logger.info("Request %s", cls.enb_instance_name)
        enb_parameters = {
            "enb_id": "0x1A2D0",
            "mme_list":  {'1': {'mme_addr': cls.cn_ipv6}},
            "plmn_list": {"Australia": {"plmn": "50501"}}
        }

        if custom_params:
            enb_parameters.update(custom_params)

        json_enb_parameters = json.dumps(enb_parameters)

        cls.retry_request(cls.request_enb_with_guid, json_enb_parameters)

    @classmethod
    def request_enb_with_guid(cls, json_enb_parameters):
        enb_instance = cls.request(cls.product, cls.enb_instance_name,
                                   filter_kw={"computer_guid": cls.comp_enb},
                                   partition_parameter_kw={
                                       '_': json_enb_parameters},
                                   software_type='enb')
        if enb_instance:
            instance_infos = cls.getInstanceInfos(cls.enb_instance_name)
            cls.enb_instance_guid = instance_infos.news['instance'][0]['reference']
            cls.request_ru1()
            cls.request_cell1()
            return True
        return False

    @classmethod
    def request_ru1(cls, custom_params=None):
        cls.logger.info("Request %s", cls.eru1_instance_name)
        ru1_parameters = {
            'ru_type':      'lopcomm',
            'ru_link_type': 'cpri',
            'cpri_link':    {
                'sdr_dev':  0,
                'sfp_port': 0,
                'mult':     16,
                'mapping':  'hw',
                'rx_delay': 25.11,
                'tx_delay': 13.77,
                'tx_dbm':   56
            },
            'mac_addr':     '00:0a:00:00:10:20',
            'n_antenna_dl': 1,
            'n_antenna_ul': 1,
            'tx_gain': -20,
            'rx_gain': -10,
            'txrx_active':  'ACTIVE',
        }
        if custom_params:
            ru1_parameters.update(custom_params)

        json_ru1_parameters = json.dumps(ru1_parameters)

        ru1_instance = cls.request(cls.product, cls.eru1_instance_name,
                                   filter_kw={
                                       "instance_guid": cls.enb_instance_guid},
                                   partition_parameter_kw={
                                       '_': json_ru1_parameters},
                                   shared=True, software_type='enb', state='started')

        for _ in range(5):
            cls.logger.info("Request %s", cls.eru1_instance_name)
            ru1_instance

        if ru1_instance:
            instance_infos = cls.getInstanceInfos(cls.eru1_instance_name)
            cls.ru1_ipv6 = instance_infos.connection_dict.get('ipv6')
            return True
        return False

    @classmethod
    def request_cell1(cls):
        cls.logger.info("Request %s", cls.ecell1_instance_name)
        cell1_parameters = {
            'cell_type':    'lte',
            'cell_kind':    'enb',
            'rf_mode':      'fdd',
            'bandwidth':    20,
            'dl_earfcn':    cls.dl_earfcn,
            'pci':          1,
            'cell_id':      '0x01',
            'tac':          '0x1234',
            'ru':           {
                'ru_type':  'ru_ref',
                'ru_ref':   cls.eru1_instance_name
            }
        }

        json_cell1_parameters = json.dumps(cell1_parameters)

        for _ in range(5):
            cls.request(cls.product, cls.ecell1_instance_name,
                        partition_parameter_kw={'_': json_cell1_parameters},
                        software_type='enb',
                        filter_kw={"instance_guid": cls.enb_instance_guid},
                        shared=True, state='started')

    # Request Core Network/SIM Card
    @classmethod
    def request_core_network(cls):
        cls.logger.info("Request %s", cls.cn_instance_name)
        core_network_parameters = json.dumps({
            "core_network_plmn": "50501",
            'external_enb_gnb': True,
        })
        cls.retry_request(cls.request_core_network_with_guid,
                          core_network_parameters)

    @classmethod
    def request_core_network_with_guid(cls, core_network_parameters):
        core_network_instance = cls.request(cls.product, cls.cn_instance_name,
                                            filter_kw={
                                                "computer_guid": cls.comp_cn},
                                            partition_parameter_kw={
                                                '_': core_network_parameters},
                                            software_type='core-network')
        if core_network_instance:
            instance_infos = cls.getInstanceInfos(cls.cn_instance_name)
            cls.cn_instance_guid = instance_infos.news['instance'][0]['reference']
            cls.cn_ipv6 = instance_infos.connection_dict.get(
                'core-network-ipv6')
            cls.request_demo_sim_cards()
            return True
        return False

    @classmethod
    def request_demo_sim_cards(cls):
        cls.logger.info("Request %s", cls.sim_instance_name)
        if cls.cn_instance_guid is None:
            cls.logger.error(
                "Core network instance GUID not set. Cannot request demo SIM cards.")
            return

        sim_card_parameters = {
            "sim_algo": "xor",
            "imsi": "505010123456789",
            "k": "00112233445566778899aabbccddeeff",
            "imeisv": "8682430000000101",
            "impi": "505010123456789@ims.mnc505.mcc001.3gppnetwork.org",
            "impu": ["505010123456789", "tel:0600000000", "tel:600"]
        }

        json_sim_card_parameters = json.dumps(sim_card_parameters)
        cls.retry_request(cls.request, cls.product, cls.sim_instance_name,
                          partition_parameter_kw={
                              '_': json_sim_card_parameters},
                          software_type='core-network',
                          filter_kw={"instance_guid": cls.cn_instance_guid},
                          shared=True, state='started')

    # Request UE/Cell/SIM
    @classmethod
    def request_ue(cls):
        cls.logger.info("Request %s", cls.ue_instance_name)
        cls.retry_request(cls.request_ue_with_guid)

    @classmethod
    def request_ue_with_guid(cls):
        ue_instance = cls.request(cls.product, cls.ue_instance_name,
                                  filter_kw={"computer_guid": cls.comp_ue},
                                  software_type='ue', state='started')
        if ue_instance:
            instance_infos = cls.getInstanceInfos(cls.ue_instance_name)
            cls.ue_instance_guid = instance_infos.news['instance'][0]['reference']
            cls.ue_com_addr = instance_infos.connection_dict.get('com_addr')
            cls.rue_addr = instance_infos.connection_dict.get('rue_bind_addr')
            cls.request_ue_cell1()
            cls.request_ue_sim()
            return True
        return False

    @classmethod
    def request_ue_cell1(cls):
        cls.logger.info("Request %s", cls.ucell1_instance_name)
        ucell1_parameters = {
            'cell_type':    'lte',
            'cell_kind':    'ue',
            'rf_mode':      'fdd',
            'dl_earfcn':    cls.dl_earfcn,
            'bandwidth': 20,
            'ru': {
                'ru_type':      'sdr',
                'ru_link_type': 'sdr',
                'sdr_dev_list': [0],
                'n_antenna_dl': 1,
                'n_antenna_ul': 1,
                'tx_gain':      60,
                'rx_gain':      40,
                'txrx_active':  'ACTIVE',
            }
        }

        json_ucell1_parameters = json.dumps(ucell1_parameters)

        cls.retry_request(cls.request, cls.product, cls.ucell1_instance_name,
                          partition_parameter_kw={'_': json_ucell1_parameters},
                          software_type='ue',
                          filter_kw={"instance_guid": cls.ue_instance_guid},
                          shared=True, state='started')

    @classmethod
    def request_ue_sim(cls):
        cls.logger.info("Request %s", cls.usim_instance_name)
        cls.wait_for_attribute('rue_addr')
        usim_parameters = {
            "ue_type": "lte",
            "rue_addr": cls.rue_addr,
            "sim_algo": "xor",
            "imsi": "505010123456789",
            "k": "00112233445566778899aabbccddeeff",
            "imeisv": "8682430000000101",
            "impi": "505010123456789@ims.mnc505.mcc001.3gppnetwork.org",
            "impu": ["505010123456789", "tel:0600000000", "tel:600"]
        }

        json_usim_parameters = json.dumps(usim_parameters)
        cls.request(cls.product, cls.usim_instance_name,
                    partition_parameter_kw={'_': json_usim_parameters},
                    software_type='ue',
                    filter_kw={"instance_guid": cls.ue_instance_guid},
                    shared=True, state='started')

    @classmethod
    def setup_websocket_connection(cls):
        # cls.waitUntilGreen(cls.ue_instance_name)
        cls.wait_for_attribute('ue_com_addr')
        cls.ws_url = f"ws://{cls.ue_com_addr}"
        cls.logger.info(f"Websocket URL: {cls.ws_url}")

        for attempt in range(cls.max_retries):
            try:
                cls.ws = create_connection(cls.ws_url)
                cls.logger.info("Websocket connection established.")
                break
            except Exception as e:
                cls.logger.error(
                    f"Websocket connection attempt {attempt + 1} failed: {e}")
                if attempt < cls.max_retries - 1:
                    time.sleep(5)

    @classmethod
    def send_udp_packet(cls, dst_address, data, dst_port=13200):
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        try:
            sock.sendto(data, (dst_address, dst_port))
            cls.logger.info(
                f"UDP packet sent successfully to {dst_address}:{dst_port}")
        except Exception as e:
            cls.logger.error(f"Failed to send UDP packet: {e}")
        finally:
            sock.close()

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
        time.sleep(30)

    def power_off(self, ue_id):
        self.assertTrue(self.ue_get()['power_on'], "UE already powered off")
        self.send({"message": "power_off", "ue_id": ue_id})
        self.recv()
        time.sleep(30)


class BBUTest(WebsocketTestClass):
    def test_ue_has_ip(self):
        """
        Tests that a User Equipment (UE) can establish a connection and receive an IP address.

        This method sets up a websocket connection, requests the status of the UE, and then
        activates transmission and reception (txrx) on the Radio Unit (RU). After activating the UE and allowing
        some time for network registration, it checks if the UE has successfully connected to the network and
        received an IPv4 address from the PDN list. If successful, the IPv4 address is logged.
        """
        BBUTest.setup_websocket_connection()
        result = self.recv()
        result = self.ue_get()
        ue_id = result['ue_id']

        custom_params = {'txrx_active':  'ACTIVE'}
        BBUTest.request_ru1(custom_params)
        time.sleep(180)

        try:
            self.power_on(ue_id)
            result = self.ue_get()
            self.logger.info(result)
            self.assertIn('pdn_list', result, "UE didn't connect")
            self.assertIn('ipv4', result['pdn_list'][0], "UE didn't get IPv4")
            self.logger.info("UE connected with ip: " +
                             result['pdn_list'][0]['ipv4'])
        finally:
            self.power_off(ue_id)

    def test_txrx_inactive(self):
        """
        Verifies that a User Equipment (UE) does not connect when Radio Unit (RU) carriers are inactive.

        This test sets up a websocket connection and configures the RU to have inactive transmission and
        reception (txrx). After attempting to power on the UE, the method checks that the UE does not establish a
        connection, evidenced by the absence of a PDN list in the UE's status.
        """
        BBUTest.setup_websocket_connection()
        result = self.recv()
        result = self.ue_get()
        ue_id = result['ue_id']

        custom_params = {'txrx_active':  'INACTIVE'}
        BBUTest.request_ru1(custom_params)
        time.sleep(180)

        try:
            self.power_on(ue_id)
            result = self.ue_get()
            self.logger.info(result)
            self.assertNotIn('pdn_list', result)
        finally:
            self.power_off(ue_id)

    def test_max_rx_sample_db(self):
        """
        Tests the alarm for saturated RX samples by setting the maximum RX sample dB to an exceptionally low value.

        This method modifies the eNodeB configuration to test if the system correctly identifies and handles the condition
        where the received signal strength (RX samples) is below a set threshold, potentially triggering a saturation alarm.
        """
        custom_params = {"max_rx_sample_db": -999}
        BBUTest.request_enb(custom_params)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-rx-saturated", expected=False)

    def test_min_rxtx_delay(self):
        """
        Checks the baseband latency by setting a minimum threshold for round-trip delay in transmission and reception.

        This method configures the eNodeB to test the baseband's ability to handle specified latencies, ensuring that
        the system can maintain synchronization and performance under constrained delay conditions.
        """
        custom_params = {"min_rxtx_delay": 99}
        BBUTest.request_enb(custom_params)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name="check-baseband-latency", expected=False)

    def test_ru_reset_and_cpri_lock_lost(self):
        """
        Tests the CPRI link lock loss and recovery by scheduling a reset of the Radio Unit (RU).

        This method schedules an RU reset one minute into the future and checks the CPRI link status immediately after
        the scheduled reset time, expecting it to be lost. After a delay, it verifies that the CPRI link lock is restored,
        demonstrating the system's resilience and recovery capabilities.
        """
        current_time = datetime.now()
        future_time = current_time + timedelta(minutes=1)
        reset_crontab_time = f"{future_time.minute} {future_time.hour} * * *"

        custom_params = {"reset_schedule": reset_crontab_time}
        BBUTest.request_ru1(custom_params)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-cpri-lock", expected=False)
        time.sleep(300)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-cpri-lock", expected=True)

    def test_vswr(self):
        """
        Tests the Voltage Standing Wave Ratio (VSWR) by temporarily setting the antenna threshold to zero and observing
        system responses.

        This method sends specific data to set the VSWR threshold to zero and checks if the system correctly identifies
        and handles the potential VSWR alarm condition. After testing, it resets the VSWR configuration to its original
        state and verifies that the system returns to normal operation.
        """
        BBUTest.wait_for_attribute('ru1_ipv6')
        dst_address = BBUTest.ru1_ipv6
        test_data = bytes(
            [0x4E, 0x01, 0x02, 0x01, 0xFF, 0x60, 0xFF, 0x0A, 0x04, 0x01, 0x00, 0x71, 0x02, 0x4E])
        reset_data = bytes(
            [0x4E, 0x01, 0x02, 0x01, 0xFF, 0x60, 0xFF, 0x0A, 0x04, 0x01, 0x19, 0x8A, 0x02, 0x4E])

        BBUTest.send_udp_packet(dst_address, test_data)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-vswr", expected=False)

        BBUTest.send_udp_packet(dst_address, reset_data)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-vswr", expected=True)

    def test_pa_over_current(self):
        """
        Tests the system's response to a power amplifier (PA) over-current condition by temporarily setting the current draw to a threshold that triggers an alarm.

        This test sends data to the Radio Unit (RU) to simulate an over-current condition on the PA. It checks the system's response to this condition by waiting for the relevant promise to indicate failure (alarm triggered). After the test, it sends a reset command to restore the PA current settings to normal levels and verifies that the system returns to a stable state without alarms.
        """
        BBUTest.wait_for_attribute('ru1_ipv6')
        dst_address = BBUTest.ru1_ipv6
        test_data = bytes(
            [0x4E, 0x01, 0x02, 0x01, 0xFF, 0x60, 0xFF, 0x04, 0x04, 0x02, 0x00, 0x00, 0x6C, 0x02, 0x4E])
        reset_data = bytes(
            [0x4E, 0x01, 0x02, 0x01, 0xFF, 0x60, 0xFF, 0x04, 0x04, 0x02, 0x20, 0x03, 0x8F, 0x02, 0x4E])

        BBUTest.send_udp_packet(dst_address, test_data)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-pa-current", expected=False)

        BBUTest.send_udp_packet(dst_address, reset_data)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-pa-current", expected=True)

    def test_pa_over_output_power(self):
        """
        Tests the system's response to a power amplifier (PA) over-output power condition by configuring the output power to exceed normal operational limits.

        This method triggers an over-output power condition by sending specific data to the Radio Unit (RU). It then observes if the system properly identifies and reacts to this condition, checking for a corresponding alarm trigger. Following the test, a reset command is issued to bring the output power back within safe operational parameters, ensuring the system's stability is restored.
        """
        BBUTest.wait_for_attribute('ru1_ipv6')
        dst_address = BBUTest.ru1_ipv6
        test_data = bytes(
            [0x4E, 0x01, 0x02, 0x01, 0xFF, 0x60, 0xFF, 0x06, 0x04, 0x02, 0x00, 0x00, 0x6E, 0x02, 0x4E])
        reset_data = bytes(
            [0x4E, 0x01, 0x02, 0x01, 0xFF, 0x60, 0xFF, 0x06, 0x04, 0x02, 0x2C, 0x01, 0x9B, 0x02, 0x4E])

        BBUTest.send_udp_packet(dst_address, test_data)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-pa-output-power", expected=False)

        BBUTest.send_udp_packet(dst_address, reset_data)
        self.waitUntilPromises(
            BBUTest.enb_instance_name, promise_name=BBUTest.eru1_instance_name + "-pa-output-power", expected=True)
