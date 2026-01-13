import json
import hashlib
import hmac
import random
import time
import slapos.testing.e2e as e2e
from websocket import create_connection

# 1767374328
DEV = True

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
                    "tx_power_dbm": 30,
                    "bandwidth": "10 MHz",
                    "dl_earfcn": 38350,
                },
                "cell2": {
                    "cell_type": "eNB",
                    "enable_cell": False,
                    "tx_power_dbm": 30
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
                  "cell_type": "lte",
                  "cell_kind": "ue",
                  "rf_mode": "tdd",
                  "ru": {
                      "ru_type": "sdr",
                      "ru_link_type": "sdr",
                      "sdr_dev_list": [
                          2
                      ],
                      "n_antenna_dl": 1,
                      "n_antenna_ul": 1,
                      "tx_gain": 90,
                      "rx_gain": 45,
                      "txrx_active": "ACTIVE"
                  },
                  "dl_earfcn": 38350,
                  "ul_earfcn": 38350,
                  "bandwidth": 10
            }
            cls.parameters["ue#ue"] = {
                  "ue_type": "lte",
                  "imsi": f"{plmn}0000000001",
                  "k": "00112233445566778899AABBCCDDEEFF",
                  "sim_algo": "milenage",
                  "opc": "000102030405060708090A0B0C0D0E0F",
                  "amf": "0x9001",
                  "sqn": "000000000000",
                  "impu": f"{plmn}0000000001",
                  "impi": f"{plmn}0000000001@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org"
            }
            for ref in cls.parameters:
              # TODO: re-enable lock
              cls.update_service(ref, "started", parameters=cls.parameters[ref], lock=False)

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
          parameters = {"_": json.dumps(instance_infos.parameter_dict["_"])}

        # Lock mechanism, only for non shared instances
        while lock and not shared:
          cls.logger.info(f"Waiting for lock to be released for {instance_name}...")
          lock = time.time()
          if sr_type == "enb-gnb":
            previous_lock = float(instance_infos.parameter_dict["_"].get("management", {}).get("lock", 0))
          else:
            previous_lock = float(instance_infos.parameter_dict["_"].get("lock", 0))
          # If previous lock is more than 6 hours old, then we assume the previous
          # test exited without properly releasing the lock
          if (lock - previous_lock) > (3600 * 6):
            parameters = json.loads(parameters["_"])
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
          parameters = json.loads(parameters["_"])
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
        # TODO: re-enable stop
        #cls.update_service("enb-gnb", "stopped", lock=False)
        #cls.update_service("core-network", "stopped", lock=False)
        #cls.update_service("ue", "stopped", lock=False)
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
    #def test_ue_has_ip(self):
    #    result = self.ue_get()
    #    ue_id = result["ue_id"]

    #    try:
    #        self.power_on(ue_id)
    #        time.sleep(5)
    #        result = self.ue_get()
    #        self.assertIn("pdn_list", result, "UE didn't connect")
    #        self.assertIn("ipv4", result["pdn_list"][0], "UE didn't get IPv4")
    #        self.logger.info("UE connected with ip: " + result["pdn_list"][0]["ipv4"])
    #    finally:
    #        self.power_off(ue_id)

    def check_ue_ip(self):

        for ref in self.parameters:
          self.update_service(ref, "started", parameters=self.parameters[ref], lock=False)

        self.logger.info("Waiting 2 minutes")
        time.sleep(2 * 60)

        self.logger.info("Waiting until instances are green")
        self.waitUntilGreen(self.enb_gnb_instance_name, timeout=60 * 3)
        self.waitUntilGreen(self.ue_instance_name)
        self.setup_websocket_connection()

        result = self.ue_get()
        ue_id = result["ue_id"]

        try:
            self.power_on(ue_id)
            time.sleep(5)
            result = self.ue_get()
            self.assertIn("pdn_list", result, "UE didn't connect")
            self.assertIn("ipv4", result["pdn_list"][0], "UE didn't get IPv4")
            self.logger.info("UE connected with ip: " + result["pdn_list"][0]["ipv4"])
        finally:
            self.power_off(ue_id)
            self.close_websocket_connection()

    def check_lte_conf(self, dl_freq, dl_earfcn, ul_earfcn, band, rf_mode, bandwidth):

        rf_info = json.loads(self.parameters["enb-gnb"]["rf-info"])
        rf_info["sdr_map"]["0"].update({
              "band": band,
              "tdd": rf_mode.upper()
            })

        self.parameters["enb-gnb"]["cell1"] = {
              "enable_cell": True,
              "cell_type": "eNB",
              "tx_power_dbm": 30,
              "bandwidth": f"{bandwidth} MHz",
              "dl_frequency": dl_freq,
              "lte_band": int(band[1:]),
            }
        self.parameters["enb-gnb"]["cell2"].update({
              "enable_cell": False,
            })
        self.parameters["enb-gnb"]["rf-info"] = json.dumps(rf_info)
        self.parameters["ue#cell"].update(
            {
              "cell_type": "lte",
              "rf_mode": rf_mode.lower(),
              "dl_earfcn": dl_earfcn,
              "ul_earfcn": ul_earfcn,
              "bandwidth": bandwidth,
            })
        self.parameters["ue#cell"].pop("dl_nr_arfcn", None)
        self.parameters["ue#cell"].pop("ul_nr_arfcn", None)
        self.parameters["ue#cell"].pop("ssb_nr_arfcn", None)

        self.check_ue_ip()

    def check_nr_conf(self, dl_freq, dl_nr_arfcn, ul_nr_arfcn, band, rf_mode, bandwidth):

        rf_info = json.loads(self.parameters["enb-gnb"]["rf-info"])
        rf_info["sdr_map"]["0"].update({
              "band": band,
              "tdd": rf_mode.upper()
            })

        self.parameters["enb-gnb"]["cell1"] = {
              "enable_cell": True,
              "cell_type": "gNB",
              "tx_power_dbm": 30,
              "nr_bandwidth": bandwidth,
              "dl_frequency": dl_freq,
              "nr_band": int(band[1:]),
            }
        self.parameters["enb-gnb"]["cell2"].update({
              "enable_cell": False,
            })
        self.parameters["enb-gnb"]["rf-info"] = json.dumps(rf_info)
        self.parameters["ue#cell"].update(
            {
              "cell_type": "nr",
              "rf_mode": rf_mode.lower(),
              "dl_nr_arfcn": dl_nr_arfcn,
              "ul_nr_arfcn": ul_nr_arfcn,
              "nr_band": int(band[1:]),
              "bandwidth": bandwidth,
            })
        self.parameters["ue#cell"].pop("dl_earfcn", None)
        self.parameters["ue#cell"].pop("ul_earfcn", None)

        self.parameters["ue#ue"]["ue_type"] = "nr"

        # Get SSB NR ARFCN
        self.logger.info("Gettting SSB NR ARFCN")
        self.update_service("enb-gnb", "started", parameters=self.parameters["enb-gnb"], lock=False)

        self.logger.info("Waiting until parameters update")
        params = self.parameters["enb-gnb"]["cell1"]
        while True:
            time.sleep(10)
            connection_params = self.getInstanceInfos(self.enb_gnb_instance_name).connection_dict
            dl_freq = float(connection_params['RADIO.dl-frequency'].removesuffix(" MHz"))
            self.logger.info(connection_params)
            bandwidth = int(connection_params['RADIO.bandwidth'].removesuffix(" MHz"))
            if dl_freq != params['dl_frequency']:
                self.logger.info(f"{dl_freq} != {params['dl_frequency']}")
                continue
            if bandwidth != params['nr_bandwidth']:
                self.logger.info(f"{bandwidth} != {params['nr_bandwidth']}")
                continue
            break
        self.parameters["ue#cell"]['ssb_nr_arfcn'] = int(connection_params['RADIO.ssb-nr-arfcn'])

        self.check_ue_ip()

    #def test_lte_B28_10(self):
    #    self.check_lte_conf(792, 9550, 27550, 'B28', 'FDD', 10)
    #def test_lte_B38_10(self):
    #    self.check_lte_conf(2600, 38050, 38050, 'B38', 'TDD', 10)
    #def test_lte_B39_10(self):
    #    self.check_lte_conf(1900, 38450, 38450, 'B39', 'TDD', 10)
    #def test_lte_B40_10(self):
    #    self.check_lte_conf(2350, 39150, 39150, 'B40', 'TDD', 10)
    #def test_lte_B42_10(self):
    #    self.check_lte_conf(3500, 42590, 42590, 'B42', 'TDD', 10)
    #def test_lte_B43_10(self):
    #    self.check_lte_conf(3700, 44590, 44590, 'B43', 'TDD', 10)
    def test_nr_N38_10(self):
        self.check_nr_conf(2600, 520000, 520000, 'B38', 'TDD', 20)

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
