import json
import hashlib
import hmac
import random
import time
import slapos.testing.e2e as e2e
from websocket import create_connection
from websocket import _exceptions

# 1767374328
DEV = True
LOCK = False
MAX_RETRY = 3

class WebsocketTestClass(e2e.EndToEndTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()

            cls.logger.info("Setting up class")
            
            if DEV:
                cls.enb_gnb_instance_name = "simbox005-enb-gnb"
                cls.core_network_instance_name = "simbox005-core-network"
                cls.core_network_sim_instance_name = "simbox005-sim"
                cls.ue_instance_name = "e2e-sb005-ue"
                cls.ue_cell_instance_name = "e2e-sb005-ue-cell"
                cls.ue_ue_instance_name = "e2e-sb005-ue-ue"
            else:
                cls.enb_gnb_instance_name = "e2e-ors70-enb-2"
                cls.core_network_instance_name = "e2e-ors70-mme-1737037360"
                cls.core_network_sim_instance_name = "e2e-ors70-sim-card-1737037360"
                cls.ue_instance_name = "e2e-sb005-ue-tagged"
                cls.ue_cell_instance_name = "e2e-sb005-ue-cell-tagged"
                cls.ue_ue_instance_name = "e2e-sb005-ue-ue-tagged"

            # Retry configurations
            cls.max_retries = 1
            cls.retry_delay = 1  # seconds

            mnc  = "99"
            mcc = "999"
            plmn = mcc + mnc
            mnc = (3 - len(mnc)) * "0" + mnc

            rf_info = {
                "sdr_map": {
                  "0": {
                    "serial": "001",
                    "version": "4.5",
                    "band": "B39",
                    "tdd": "TDD",
                    "model": "SDR100"
                  },
                  "1": {
                    "serial": "001",
                    "version": "4.5",
                    "band": "B39",
                    "tdd": "TDD",
                    "model": "SDR100"
                  }
                },
                "flavour": "BBU"
              }

            cls.parameters = {}
            cls.parameters["enb-gnb"] = {
                "cell1": {
                    "cell_type": "eNB",
                    "enable_cell": True,
                    "tx_power_dbm": 0,
                    "rx_gain": 35,
                },
                "cell2": {
                    "cell_type": "eNB",
                    "enable_cell": False,
                    "tx_power_dbm": 0,
                    "rx_gain": 35,
                },
                "nodeb": {
                    "n_antenna_dl": 1,
                    "n_antenna_ul": 1,
                    "plmn_list": [
                        {
                            "plmn": plmn,
                        },
                    ],
                    "plmn_list_5g": [
                        {
                            "plmn": plmn,
                            "tac": "1",
                        },
                    ],
                },
                "management": {
                    "xlog_enabled": False,
                    "xlog_forwarding_enabled": False,
                },
                "rf-info": json.dumps(rf_info)
            }
            cls.parameters["core-network#sim"] = {
                "sim_algo": "milenage",
                "plmn": plmn,
                "msin": "0000000001",
                "opc": "000102030405060708090A0B0C0D0E0F",
                "k": "00112233445566778899AABBCCDDEEFF",
            }
            cls.parameters["core-network"] = {
                   "core_network_plmn": plmn,
                   "iperf3": 1,
                   "network_name": "E2E Testing",
                   "network_short_name": "E2E Testing",
            }
            cls.parameters["ue"] = {
            }
            cls.parameters["ue#cell"] = {
                  "cell_kind": "ue",
                  "ru": {
                      "ru_type": "sdr",
                      "ru_link_type": "sdr",
                      "sdr_dev_list": [
                          1
                      ],
                      "n_antenna_dl": 1,
                      "n_antenna_ul": 1,
                      "tx_gain": 70,
                      "rx_gain": 35,
                      "txrx_active": "ACTIVE"
                  },
            }
            cls.parameters["ue#ue"] = {
                  "imsi": f"{plmn}0000000001",
                  "k": "00112233445566778899AABBCCDDEEFF",
                  "sim_algo": "milenage",
                  "opc": "000102030405060708090A0B0C0D0E0F",
                  "amf": "0x9001",
                  "sqn": "000000000000",
                  "impu": f"{plmn}0000000001",
                  "impi": f"{plmn}0000000001@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org"
            }
            if LOCK:
              for ref in cls.parameters:
                cls.update_service(ref, "started", parameters=cls.parameters[ref], lock=True)

        except Exception as e:
            cls.logger.error("Error during setup: " + str(e))
            # Ensure cleanup
            cls.tearDownClass()
            raise

    @classmethod
    def setup_websocket_connection(cls):
        connection_params = cls.getInstanceInfos(cls.ue_instance_name).connection_dict
        cls.waitUntilGreen(cls.ue_instance_name)
        cls.ws_host = connection_params.get("websocket-hostname")
        cls.ws_port = connection_params.get("websocket-port")
        cls.ws_pass = connection_params.get("websocket-password")
        cls.ws_url = f"wss://{cls.ws_host}/websocket:{cls.ws_port}"

        cls.logger.info(f"Websocket URL: {cls.ws_url}")

        cls.ws = create_connection(cls.ws_url)
        cls.logger.info("Websocket connection established.")
        data = json.loads(cls.ws.recv())
        res = hmac.new(
          "{}:{}:{}".format(data["type"], cls.ws_pass, data["name"]).encode(),
          msg=data["challenge"].encode(),
          digestmod=hashlib.sha256
        ).hexdigest()
        msg = {"message": "authenticate", "res": res}
        cls.ws.send(json.dumps(msg))
        cls.ws.recv()
        cls.logger.info("Websocket authentication established.")

    @classmethod
    def update_service(cls, name, state, parameters=None, lock=None):
        sr_type = name.split("#")[0]
        shared = "#" in name
        name = name.replace("#", "_").replace("-", "_")
        instance_name = getattr(cls, f"{name}_instance_name")
        instance_infos = cls.getInstanceInfos(instance_name)
        if parameters:
          parameters = {"_": json.dumps(parameters)}
        else:
          parameters = {"_": json.dumps(instance_infos.parameter_dict.get("_", {}))}

        # Lock mechanism, only for non shared instances
        while lock and not shared:
          cls.logger.info(f"Waiting for lock to be released for {instance_name}...")
          lock = time.time()
          if sr_type == "enb-gnb":
            previous_lock = float(instance_infos.parameter_dict.get("_", {}).get("management", {}).get("lock", 0))
          else:
            previous_lock = float(instance_infos.parameter_dict.get("_", {}).get("lock", 0))
          # If previous lock is more than 6 hours old, then we assume the previous
          # test exited without properly releasing the lock
          if (lock - previous_lock) > (3600 * 6):
            parameters = json.loads(parameters.get("_", {}))
            if sr_type == "enb-gnb":
              parameters.setdefault("management", {})["lock"] = str(lock)
            else:
              parameters["lock"] = str(lock)
            parameters = {"_": json.dumps(parameters)}
            break
          # Sleep a random amount between 1 and 10 minutes to avoid multiple test
          # suites getting the lock at the same time
          time.sleep(random.randint(60, 10 * 60))
          instance_infos = cls.getInstanceInfos(instance_name)
        # Unlock
        if lock == False:
          parameters = json.loads(parameters.get("_", {}))
          if sr_type == "enb-gnb":
            parameters.setdefault("management", {}).pop("lock", None)
          else:
            parameters.pop("lock", None)
          parameters = {"_": json.dumps(parameters)}

        cls.logger.info(f"Update {instance_name}")
        args = [instance_infos.software_url, instance_name,]
        kwargs = {
                      "shared"                : shared,
                      "partition_parameter_kw": parameters,
                      "software_type"         : sr_type,
                      "state"                 : state,}
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
    def close_websocket_connection(cls):
        if hasattr(cls, "ws") and cls.ws is not None:
            cls.logger.info("Closing websocket")
            cls.ws.close()

    @classmethod
    def tearDownClass(cls):
        cls.close_websocket_connection()
        if LOCK:
          cls.update_service("enb-gnb", "stopped", lock=False)
          cls.update_service("core-network", "stopped", lock=False)
          cls.update_service("ue", "stopped", lock=False)
        # Don"t call super().tearDownClass as we don"t want to destroy requested instances

    def send(self, msg):
        self.ws.send(json.dumps(msg))
    def recv(self):
        return json.loads(self.ws.recv())

    def ue_get(self):
        self.send({"message": "ue_get"})
        result = self.recv()

        if "message" not in result:
            raise ValueError(f"Unexpected response format: {result}")

        if "ue_list" in result:
            if not result["ue_list"]:
                raise ValueError(f"No UE found in response: {result}")
            return result["ue_list"][0]
        else:
            return result

    def power_on(self, ue_id):
        self.assertFalse(self.ue_get()["power_on"], "UE already powered on")
        self.send({"message": "power_on", "ue_id": ue_id})
        self.recv()

    def power_off(self, ue_id):
        self.assertTrue(self.ue_get()["power_on"], "UE already powered off")
        self.send({"message": "power_off", "ue_id": ue_id})
        self.recv()

class ORSTest(WebsocketTestClass):

    def check_ue_ip(self):

        for ref in self.parameters:
          self.update_service(ref, "started", parameters=self.parameters[ref], lock=False)

        self.logger.info("Waiting until instances are green")
        self.waitUntilGreen(self.enb_gnb_instance_name, timeout=60 * 3)
        self.waitUntilGreen(self.ue_instance_name)

        retry = True

        for i in range(MAX_RETRY):
            if not retry:
              break
            retry = False
            ue_id = None
            try:
                self.setup_websocket_connection()
                result = self.ue_get()
                ue_id = result["ue_id"]
                self.power_on(ue_id)
                time.sleep(10)
                result = self.ue_get()
                self.assertIn("pdn_list", result, "UE didn't connect")
                self.assertIn("ipv4", result["pdn_list"][0], "UE didn't get IPv4")
                self.logger.info("UE connected with ip: " + result["pdn_list"][0]["ipv4"])
            except (_exceptions.WebSocketConnectionClosedException, _exceptions.WebSocketBadStatusException, json.decoder.JSONDecodeError):
                retry = True
            finally:
                try:
                    if ue_id:
                      self.power_off(ue_id)
                    self.close_websocket_connection()
                except _exceptions.WebSocketConnectionClosedException:
                    pass

    def check_ue_connect(self, nr, band, rf_mode, bandwidth, freq=None):

        self.logger.info(f"Checking following configuration: 5G={nr}, {band}, {rf_mode}, {bandwidth}, {freq}")

        rf_info = json.loads(self.parameters["enb-gnb"]["rf-info"])
        rf_info["sdr_map"]["0"].update({
              "band": band,
              "tdd": rf_mode.upper()
            })

        self.parameters["enb-gnb"]["cell1"] = {
              "enable_cell": True,
              "cell_type": "gNB" if nr else "eNB",
            }
        if freq:
            self.parameters["enb-gnb"]["cell1"]["dl_frequency"] = freq

        self.parameters["enb-gnb"]["cell2"].update({
              "enable_cell": False,
            })
        self.parameters["enb-gnb"]["rf-info"] = json.dumps(rf_info)
        self.parameters["ue#cell"].update(
            {
              "cell_type": "nr" if nr else "lte",
              "rf_mode": rf_mode.lower(),
              "bandwidth": bandwidth,
            })
        if nr:
            self.parameters["enb-gnb"]["cell1"]["nr_bandwidth"] = bandwidth
            self.parameters["ue#cell"].pop("dl_earfcn", None)
            self.parameters["ue#cell"].pop("ul_earfcn", None)
            self.parameters["ue#ue"]["ue_type"] = "nr"
        else:
            self.parameters["enb-gnb"]["cell1"]["bandwidth"] = f"{bandwidth} MHz"
            self.parameters["ue#cell"].pop("dl_nr_arfcn", None)
            self.parameters["ue#cell"].pop("ul_nr_arfcn", None)
            self.parameters["ue#ue"]["ue_type"] = "lte"

        self.logger.info("Gettting eNB / gNB connection parameters")
        self.update_service("enb-gnb", "started", parameters=self.parameters["enb-gnb"], lock=False)

        self.logger.info("Waiting until parameters update")
        params = self.parameters["enb-gnb"]["cell1"]
        for i in range(30):
            time.sleep(10)
            connection_params = self.getInstanceInfos(self.enb_gnb_instance_name).connection_dict
            model = connection_params['HARDWARE.ors-version'].split(' ')[2]
            try:
              bandwidth = int(connection_params['RADIO.bandwidth'].removesuffix(" MHz"))
            except ValueError:
              continue
            if not model.startswith(band):
                self.logger.info(f"{model} != {band}")
                continue
            if nr and bandwidth != params['nr_bandwidth']:
                self.logger.info(f"{bandwidth} != {params['nr_bandwidth']}")
                continue
            if not nr and bandwidth != int(params['bandwidth'].removesuffix(" MHz")):
                self.logger.info(f"{bandwidth} != " + params['bandwidth'].removesuffix(" MHz"))
                continue
            break
        else:
            self.assertTrue(False, "Service was not ready in time")

        float(connection_params['POWER.tx-gain'].removesuffix(" dB"))
            
        if nr:
            self.parameters["ue#cell"].update({
              "ssb_nr_arfcn": int(connection_params['RADIO.ssb-nr-arfcn']),
              "dl_nr_arfcn": int(connection_params['RADIO.dl-arfcn']),
              "ul_nr_arfcn": int(connection_params['RADIO.ul-arfcn']),
              "nr_band": int(connection_params['RADIO.band'][1:]),
            })
        else:
            self.parameters["ue#cell"].update({
              "dl_earfcn": int(connection_params['RADIO.dl-arfcn']),
              "ul_earfcn": int(connection_params['RADIO.ul-arfcn']),
            })
        tx_gain = 80
        rx_gain = 40
        tx_power_list = [
            (500 ,  12.0),
            (1000,  12.0),
            (1500,  9.0),
            (2000,  8.0),
            (2500,  4.0),
            (3000,  5.0),
            (3500,  3.0),
            (4000,  -3.0),
            (4500,  -9.0),
            (5000,  -20.0),
        ]
        for freq,db in tx_power_list:
            if float(connection_params['RADIO.dl-frequency'].removesuffix(" MHz")) < freq:
                tx_gain -= db
                rx_gain -= db
                break
        self.parameters["enb-gnb"]["cell1"]["tx_gain"] = tx_gain
        self.parameters["enb-gnb"]["cell1"]["rx_gain"] = rx_gain
        self.parameters["ue#cell"]["tx_gain"] = tx_gain
        self.parameters["ue#cell"]["rx_gain"] = rx_gain

        self.parameters["enb-gnb"]["cell1"].pop("tx_power_dbm", None)

        self.check_ue_ip()

    def test_lte_B28_10(self):
        self.check_ue_connect(False, 'B28', 'FDD', 10)
    def test_lte_B38_10(self):
        self.check_ue_connect(False, 'B38', 'TDD', 10)
    def test_lte_B39_10(self):
        self.check_ue_connect(False, 'B39', 'TDD', 10)
    def test_lte_B40_10(self):
        self.check_ue_connect(False, 'B40', 'TDD', 10)
    def test_lte_B42_10(self):
        self.check_ue_connect(False, 'B42', 'TDD', 10)
    def test_lte_B43_10(self):
        self.check_ue_connect(False, 'B43', 'TDD', 10)
    def test_nr_B28_20(self):
        self.check_ue_connect(True, 'B28', 'FDD', 20)
    def test_nr_B38_20(self):
        self.check_ue_connect(True, 'B38', 'TDD', 20)
    def test_nr_B39_20(self):
        self.check_ue_connect(True, 'B39', 'TDD', 20)
    def test_nr_B40_20(self):
        self.check_ue_connect(True, 'B40', 'TDD', 20)
    def test_nr_N77_20(self):
        self.check_ue_connect(True, 'N77', 'TDD', 20)
    def test_nr_B42_20(self):
        self.check_ue_connect(True, 'B42', 'TDD', 20)
    def test_nr_B43_20(self):
        self.check_ue_connect(True, 'B43', 'TDD', 20)
    def test_nr_N79_20(self):
        self.check_ue_connect(True, 'N79', 'TDD', 20)

    # TODO: uncomment these tests
    #def test_max_rx_sample_db(self):
    #    custom_params = {}
    #    custom_params.update(self.parameters["enb"])
    #    custom_params.update({"max_rx_sample_db": -99})
    #    self.update_service("enb", "started", custom_params)
    #    self.waitUntilPromises(ORSTest.enb_instance_name, promise_name="check-rx-saturated", expected=False)

    #def test_min_rxtx_delay(self):
    #    # Fixed by 9798ef1e, change `expected` to False when released
    #    custom_params = {}
    #    custom_params.update(self.parameters["enb"])
    #    custom_params.update({"min_rxtx_delay": 99})
    #    self.update_service("enb", "started", custom_params)
    #    self.waitUntilPromises(ORSTest.enb_instance_name, promise_name="check-baseband-latency", expected=True)
