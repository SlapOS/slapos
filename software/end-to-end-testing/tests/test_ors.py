import json
import hashlib
import hmac
import random
import time
import slapos.testing.e2e as e2e
from websocket import create_connection
from websocket import _exceptions

CHECK_PROMISE      = True       # Disable to run tests faster
RESET              = True       # Disable this if you already have the services in a good state to quickly run a single test
LOCK               = False      # Disable to run tests faster, activates lock mechanism to prevent conflict if two tests run at the same time on the same services
DEBUG              = False      # Sleep for 20 minutes after failure to give time to debug
DEV                = True       # Use DEV services
MAX_RETRY          = 3          # Max retries to connect UE after services have been checked
RERUN_TEST         = 1767374328 # Increase to force test suite to run test again

RESET_DONE = False

class WebsocketTestClass(e2e.EndToEndTestCase):
    @classmethod
    def setUpClass(cls):
        global RESET_DONE
        try:
            super().setUpClass()

            cls.logger.info("Setting up class")
            
            if DEV:
                cls.enb_gnb_instance_name = "simbox005-enb-gnb"
                cls.core_network_instance_name = "simbox005-core-network"
                cls.core_network_sim_instance_name = "simbox005-simcard"
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

            cls.reset_parameters()

            # Update gNB and UE to disable them to make sure they restart
            if RESET:
                for ref in cls.parameters:
                    if LOCK:
                        cls.logger.info(f"Resetting {ref}")
                        cls.update_service(ref, "started", parameters=cls.parameters[ref], lock=True)
                    else:
                        if not RESET_DONE:
                            cls.logger.info(f"Resetting {ref}")
                            cls.update_service(ref, "started", parameters=cls.parameters[ref], lock=False)
                RESET_DONE = True
                time.sleep(60)

        except Exception as e:
            cls.logger.error("Error during setup: " + str(e))
            # Ensure cleanup
            cls.tearDownClass()
            raise

    @classmethod
    def setup_websocket_connection(cls, name, ws_host, ws_port, ws_pass):
        ws_url = f"wss://{ws_host}/websocket:{ws_port}"

        cls.logger.info(f"{name} Websocket URL: {ws_url}")

        ws = create_connection(ws_url)
        cls.logger.info(f"{name} Websocket connection established.")
        data = json.loads(ws.recv())
        res = hmac.new(
          "{}:{}:{}".format(data["type"], ws_pass, data["name"]).encode(),
          msg=data["challenge"].encode(),
          digestmod=hashlib.sha256
        ).hexdigest()
        msg = {"message": "authenticate", "res": res}
        ws.send(json.dumps(msg))
        ws.recv()
        cls.logger.info(f"{name} Websocket authentication established.")
        return ws

    @classmethod
    def setup_adb_websocket_connection(cls):
        # TODO: do this properly
        from os.path import expanduser
        with open(expanduser('~/adb-websocket-address'), 'r') as f:
            ws_url = f.read().strip()

        cls.logger.info(f"ADB Websocket URL: {ws_url}")

        ws = create_connection(ws_url)
        cls.logger.info(f"ADB Websocket connection established.")
        data = json.loads(ws.recv())
        cls.adb_ws = ws

    def adb_airplane_enable(self):
        self.adb_ws.send(json.dumps({"message": "airplane_enable"}))
        return self.adb_ws.recv()

    def adb_airplane_disable(self):
        self.adb_ws.send(json.dumps({"message": "airplane_disable"}))
        return self.adb_ws.recv()

    @classmethod
    def setup_ue_websocket_connection(cls):
        connection_params = cls.getInstanceInfos(cls.ue_instance_name).connection_dict
        ws_host = connection_params.get("websocket-hostname")
        ws_port = connection_params.get("websocket-port")
        ws_pass = connection_params.get("websocket-password")
        cls.ue_ws = cls.setup_websocket_connection("UE", ws_host, ws_port, ws_pass)

    @classmethod
    def setup_enb_websocket_connection(cls):
        connection_params = cls.getInstanceInfos(cls.enb_gnb_instance_name).connection_dict
        ws_host = connection_params.get("URL.websocket-hostname")
        ws_port = connection_params.get("URL.websocket-port")
        ws_pass = connection_params.get("URL.websocket-password")
        cls.enb_ws = cls.setup_websocket_connection("eNB / gNB", ws_host, ws_port, ws_pass)

    @classmethod
    def setup_core_network_websocket_connection(cls):
        connection_params = cls.getInstanceInfos(cls.core_network_instance_name).connection_dict
        ws_host = connection_params.get("URL.websocket-mme-hostname")
        ws_port = connection_params.get("URL.websocket-mme-port")
        ws_pass = connection_params.get("URL.websocket-mme-password")
        cls.core_network_ws = cls.setup_websocket_connection("Core Network", ws_host, ws_port, ws_pass)

    @classmethod
    def setup_ims_websocket_connection(cls):
        connection_params = cls.getInstanceInfos(cls.core_network_instance_name).connection_dict
        ws_host = connection_params.get("URL.websocket-ims-hostname")
        ws_port = connection_params.get("URL.websocket-ims-port")
        ws_pass = connection_params.get("URL.websocket-ims-password")
        cls.ims_ws = cls.setup_websocket_connection("IMS", ws_host, ws_port, ws_pass)

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
    def close_adb_websocket_connection(cls):
        if hasattr(cls, "adb_ws") and cls.adb_ws is not None:
            cls.logger.info("Closing ADB websocket")
            try:
                cls.adb_ws.close()
            except _exceptions.WebSocketConnectionClosedException:
                pass

    @classmethod
    def close_ue_websocket_connection(cls):
        if hasattr(cls, "ue_ws") and cls.ue_ws is not None:
            cls.logger.info("Closing UE websocket")
            try:
                cls.ue_ws.close()
            except _exceptions.WebSocketConnectionClosedException:
                pass

    @classmethod
    def close_enb_websocket_connection(cls):
        if hasattr(cls, "enb_ws") and cls.enb_ws is not None:
            cls.logger.info("Closing eNB / gNB websocket")
            try:
                cls.enb_ws.close()
            except _exceptions.WebSocketConnectionClosedException:
                pass

    @classmethod
    def close_core_network_websocket_connection(cls):
        if hasattr(cls, "core_network_ws") and cls.core_network_ws is not None:
            cls.logger.info("Closing Core Network websocket")
            try:
                cls.core_network_ws.close()
            except _exceptions.WebSocketConnectionClosedException:
                pass

    @classmethod
    def close_ims_websocket_connection(cls):
        if hasattr(cls, "ims_ws") and cls.ims_ws is not None:
            cls.logger.info("Closing IMS websocket")
            try:
                cls.ims_ws.close()
            except _exceptions.WebSocketConnectionClosedException:
                pass

    @classmethod
    def tearDownClass(cls):
        cls.close_ue_websocket_connection()
        cls.close_enb_websocket_connection()
        cls.close_core_network_websocket_connection()
        cls.close_ims_websocket_connection()
        if LOCK:
          cls.update_service("enb-gnb", "stopped", lock=False)
          cls.update_service("core-network", "stopped", lock=False)
          cls.update_service("ue", "stopped", lock=False)
        # Don"t call super().tearDownClass as we don"t want to destroy requested instances

    @classmethod
    def reset_parameters(cls):
        mnc  = "99"
        mcc = "999"
        plmn = mcc + mnc
        mnc = (3 - len(mnc)) * "0" + mnc

        rf_info = {
            "sdr_map": {
              "0": {
                "serial": "001",
                "sdr_dev": "2",
                "version": "4.5",
                "band": "B39",
                "tdd": "TDD",
                "model": "SDR100"
              },
              "1": {
                "serial": "001",
                "sdr_dev": "3",
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
                "enable_cell": "Disable eNB",
            },
            "cell2": {
                "enable_cell": "Disable eNB",
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
                        "tac": "100",
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
               "amarisoft_version": "2026-09-11.1789372267",
        }
        cls.parameters["ue"] = {
        }
        cls.parameters["ue#cell"] = {
              "cell_kind": "ue",
              "ru": {
                  "ru_type": "sdr",
                  "ru_link_type": "sdr",
                  "sdr_dev_list": [
                      3
                  ],
                  "n_antenna_dl": 1,
                  "n_antenna_ul": 1,
                  "txrx_active": "ACTIVE"
              },
              "dl_earfcn": 0,
              "cell_type": "lte",
              "rf_mode": "tdd",
              "bandwidth": 20,
        }
        cls.parameters["ue#ue"] = {
              "imsi": f"{plmn}0000000001",
              "k": "00112233445566778899AABBCCDDEEFF",
              "sim_algo": "milenage",
              "opc": "000102030405060708090A0B0C0D0E0F",
              "amf": "0x9001",
              "sqn": "000000000000",
              "impu": f"{plmn}0000000001",
              "impi": f"{plmn}0000000001@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org",
              "ue_type": "lte"
        }

    def ue_send(self, msg):
        self.ue_ws.send(json.dumps(msg))
    def ue_recv(self):
        return json.loads(self.ue_ws.recv())

    def enb_send(self, msg):
        self.enb_ws.send(json.dumps(msg))
    def enb_recv(self):
        return json.loads(self.enb_ws.recv())

    def ue_config_get_cell(self):
        self.ue_send({"message": "config_get"})
        result = self.ue_recv()
        return list(result["cells"].values())[0]

    def ue_check_cpu(self):
        self.ue_send({"message": "stats", "rf": True})
        result = self.ue_recv()
        return bool(int(result["rf"]["tx_count"]))

    def ue_quit(self):
        self.ue_send({"message": "quit"})

    def enb_config_get_cell(self):
        self.enb_send({"message": "config_get"})
        result = self.enb_recv()
        if "nr_cells" in result:
            return list(result["nr_cells"].values())[0]
        else:
            return list(result["cells"].values())[0]

    def core_network_ue_get(self):
        self.core_network_ws.send(json.dumps({"message": "ue_get"}))
        result = json.loads(self.core_network_ws.recv())

        return result

    def ims_ue_get(self):
        self.ims_ws.send(json.dumps({"message": "users_get"}))
        result = json.loads(self.ims_ws.recv())

        return result

    def enb_ue_get(self):
        self.enb_send({"message": "ue_get"})
        result = self.enb_recv()

        return result

    def ue_get(self):
        self.ue_send({"message": "ue_get"})
        result = self.ue_recv()

        if "message" not in result:
            raise ValueError(f"Unexpected response format: {result}")

        if "ue_list" in result:
            if not result["ue_list"]:
                raise ValueError(f"No UE found in response: {result}")
            return result["ue_list"][0]
        else:
            return result

    def power_on(self, ue_id):
        for i in range(10):
            if not self.ue_get()["power_on"]:
                break
            self.power_off(ue_id)
            time.sleep(1)
        self.assertFalse(self.ue_get()["power_on"], "UE already powered on")
        self.ue_send({"message": "power_on", "ue_id": ue_id})
        self.ue_recv()

    def power_off(self, ue_id):
        self.assertTrue(self.ue_get()["power_on"], "UE already powered off")
        self.ue_send({"message": "power_off", "ue_id": ue_id})
        self.ue_recv()

class ORSTest(WebsocketTestClass):

    def wait_until_ready(self, nr, dl_arfcn, wait_ue=True, wait_core_network=True):

        if CHECK_PROMISE:
            self.logger.info("Waiting until instances are green")
            time.sleep(5 * 60)
            self.waitUntilGreen(self.enb_gnb_instance_name, timeout=60 * 2)
            if wait_ue:
                self.waitUntilGreen(self.ue_instance_name, timeout=60 * 2)
            if wait_core_network:
                self.waitUntilGreen(self.core_network_instance_name, timeout=60 * 2)
        else:
            time.sleep(60)

        for i in range(13):
            if i == 12:
                self.assertTrue(False, "Service was not ready in time")
            try:
                self.logger.info("Setup eNB Websocket")
                self.setup_enb_websocket_connection()
                if wait_ue:
                    self.logger.info("Setup UE Websocket")
                    self.setup_ue_websocket_connection()

                if wait_ue and not self.ue_check_cpu():
                    self.logger.info("UE TRX SDR is stuck, lteue will restart")
                    self.ue_quit()
                    time.sleep(20)
                    raise Exception

                enb_cell = self.enb_config_get_cell()
                if wait_ue:
                    ue_cell = self.ue_config_get_cell()
                if nr:
                    if enb_cell['dl_nr_arfcn'] != dl_arfcn:
                        raise Exception
                    if wait_ue and ue_cell['dl_earfcn'] != dl_arfcn:
                        raise Exception
                    self.logger.info(f"checked dl_nr_arfcn is {enb_cell['dl_nr_arfcn']}")
                else:
                    if enb_cell['dl_earfcn'] != dl_arfcn:
                        raise Exception
                    if wait_ue and ue_cell['dl_earfcn'] != dl_arfcn:
                        raise Exception
                    self.logger.info(f"checked dl_earfcn is {enb_cell['dl_earfcn']}")
                break
            except Exception as e:
                self.logger.info(f"Exception: {e}")
                time.sleep(10)
            finally:
                self.close_enb_websocket_connection()
                if wait_ue:
                    self.close_ue_websocket_connection()

    def check_lteue_ip(self):

        retry = True

        for i in range(MAX_RETRY):
            if not retry:
              break
            retry = False
            ue_id = None
            try:
                self.setup_ue_websocket_connection()
                result = self.ue_get()
                ue_id = result["ue_id"]
                self.power_on(ue_id)
                time.sleep(10)
                result = self.ue_get()
                if DEBUG and "pdn_list" not in result or "ipv4" not in result["pdn_list"][0]:
                    self.logger.info("UE did not connect, sleeping 20 minutes...")
                    time.sleep(1200)
                self.assertIn("pdn_list", result, "UE didn't connect")
                self.assertIn("ipv4", result["pdn_list"][0], "UE didn't get IPv4")
                self.logger.info("UE connected with ip: " + result["pdn_list"][0]["ipv4"])
            except (_exceptions.WebSocketConnectionClosedException, _exceptions.WebSocketBadStatusException, json.decoder.JSONDecodeError):
                retry = True
                self.power_off(ue_id)
            finally:
                try:
                    if ue_id:
                      self.power_off(ue_id)
                except _exceptions.WebSocketConnectionClosedException:
                    pass
                self.close_ue_websocket_connection()

    def config_enb_gnb(self, nr, band, rf_mode, bandwidth=None, freq=None, enb_params={}):

        self.reset_parameters()

        if freq:
            self.parameters["enb-gnb"]["cell1"]["dl_frequency"] = freq
        self.parameters["enb-gnb"]["cell1"]["enable_cell"] = f'Enable {"gNB" if nr else "eNB"}'
        self.parameters["enb-gnb"]["cell2"]["enable_cell"] = 'Disable eNB'

        rf_info = json.loads(self.parameters["enb-gnb"]["rf-info"])
        rf_info["sdr_map"]["0"].update({
              "band": band,
              "tdd": rf_mode.upper()
            })
        self.parameters["enb-gnb"]["rf-info"] = json.dumps(rf_info)

        if bandwidth:
            if nr:
                self.parameters["enb-gnb"]["cell1"]["nr_bandwidth"] = f"{bandwidth} MHz"
            else:
                self.parameters["enb-gnb"]["cell1"]["bandwidth"] = f"{bandwidth} MHz"

        self.parameters["enb-gnb"].setdefault("cell1", {}).update(enb_params.get("cell1", {}))
        self.parameters["enb-gnb"].setdefault("nodeb", {}).update(enb_params.get("nodeb", {}))

    def check_enb_gnb(self, nr, band, bandwidth=None, freq=None, check={}, check_plmn="99999"):

        self.logger.info("Update eNB / gNB parameters")
        self.update_service("enb-gnb", "started", parameters=self.parameters["enb-gnb"], lock=False)
        self.logger.info("Update Core Network parameters")
        self.update_service("core-network", "started", parameters=self.parameters["core-network"], lock=False)

        self.logger.info("Waiting until parameters update")
        params = self.parameters["enb-gnb"]["cell1"]
        for i in range(30):
            time.sleep(10)
            connection_params     = self.getInstanceInfos(self.enb_gnb_instance_name).connection_dict
            connection_params_mme = self.getInstanceInfos(self.core_network_instance_name).connection_dict
            plmn = connection_params_mme['CORE.plmn']
            model = connection_params['HARDWARE.ors-version'].split(' ')[2]
            try:
              connection_parameter_bandwidth = float(connection_params.get('RADIO.bandwidth', " MHz").removesuffix(" MHz"))
            except ValueError:
              self.logger.info(f"Bandwidth missing in connection parameters")
              continue
            if bandwidth:
                if bandwidth != connection_parameter_bandwidth:
                    self.logger.info(f'{bandwidth} != {connection_parameter_bandwidth}')
                    continue
            if not model.startswith(band):
                self.logger.info(f"{model} != {band}")
                continue
            if freq:
                configured_freq = float(connection_params["RADIO.dl-frequency"].removesuffix(" MHz"))
                if abs(configured_freq - freq) > 0.5:
                    self.logger.info(f'{configured_freq} != {freq}')
                    continue
            if plmn != check_plmn:
                self.logger.info(f'{plmn} != {check_plmn}')
                continue
            for c in check:
                if connection_params.get(c) != check[c]:
                    self.logger.info(f'{c} connection parameter mismatch: {connection_params[c]} != {check[c]}')
                    break
                else:
                    self.logger.info(f'{c} connection parameter match: {connection_params[c]} = {check[c]}')
            else:
                break
            continue
        else:
            self.assertTrue(False, "Service was not ready in time")
        self.logger.info("Parameters updated")

        float(connection_params['POWER.tx-gain'].removesuffix(" dB"))
            
        tx_gain = 80
        rx_gain = 44
        tx_gain_gnb = 80
        rx_gain_gnb = 44
        tx_power_list = [
            (500 ,  20.0),
            (1000,  20.0),
            (1500,  20.0),
            (2000,  13.0),
            (2500,  13.0),
            (3000,  13.0),
            (3500,  13.0),
            (4000,  0),
            (4500,  0),
            (5000,  0),
        ]
        rx_power_list = [
            (500 ,  9.0),
            (1000,  9.0),
            (1500,  9.0),
            (2000,  8.0),
            (2500,  8.0),
            (3000,  8.0),
            (3500,  6.0),
            (4000,  6.0),
            (4500,  1.0),
            (5000,  0.0),
        ]
        for freq,db in tx_power_list:
            if float(connection_params['RADIO.dl-frequency'].removesuffix(" MHz")) < freq:
                tx_gain -= db
                rx_gain -= db
                tx_gain_gnb -= db
                rx_gain_gnb -= db
                break
        self.parameters["enb-gnb"]["cell1"]["tx_gain"] = tx_gain_gnb
        self.parameters["enb-gnb"]["cell1"]["rx_gain"] = rx_gain_gnb
        self.parameters["enb-gnb"]["cell1"].pop("tx_power_dbm", None)

        ue_params = {
            "tx_gain": tx_gain,
            "rx_gain": rx_gain,
            "bandwidth": connection_parameter_bandwidth,
        }
        if nr:
            ue_params.update({
                "ssb_nr_arfcn": int(connection_params['RADIO.ssb-nr-arfcn']),
                "dl_nr_arfcn": int(connection_params['RADIO.dl-nr-arfcn']),
                "ul_nr_arfcn": int(connection_params['RADIO.ul-nr-arfcn']),
                "nr_band": int(connection_params['RADIO.band'][1:]),
            })
        else:
            ue_params.update({
                "dl_earfcn": int(connection_params['RADIO.dl-earfcn']),
                "ul_earfcn": int(connection_params['RADIO.ul-earfcn']),
            })
        return ue_params

    def setup_enb_gnb(self, nr, band, rf_mode, bandwidth=None, freq=None, enb_params={}, check={}):

        self.config_enb_gnb(nr, band, rf_mode, bandwidth=bandwidth, freq=freq, enb_params=enb_params)
        return self.check_enb_gnb(nr, band, bandwidth=bandwidth, freq=freq, check=check)

    def setup_ue(self, nr, rf_mode, ue_params, ue_cell_params):

        self.parameters["ue#cell"].update(
            {
              "cell_type": "nr" if nr else "lte",
              "rf_mode": rf_mode.lower(),
              "bandwidth": ue_params["bandwidth"],
              "rx_to_tx_latency": 4,
            })
        if nr:
            self.parameters["ue#cell"].pop("dl_earfcn", None)
            self.parameters["ue#cell"].pop("ul_earfcn", None)
            self.parameters["ue#ue"]["ue_type"] = "nr"
        else:
            self.parameters["ue#cell"].pop("dl_nr_arfcn", None)
            self.parameters["ue#cell"].pop("ul_nr_arfcn", None)
            self.parameters["ue#ue"]["ue_type"] = "lte"

        self.parameters["ue#cell"].update(ue_cell_params)

        if nr:
            self.parameters["ue#cell"].update({
              "ssb_nr_arfcn": ue_params["ssb_nr_arfcn"],
              "dl_nr_arfcn" : ue_params["dl_nr_arfcn"],
              "ul_nr_arfcn" : ue_params["ul_nr_arfcn"],
              "nr_band"     : ue_params["nr_band"],
            })
        else:
            self.parameters["ue#cell"].update({
              "dl_earfcn": ue_params["dl_earfcn"],
              "ul_earfcn": ue_params["ul_earfcn"],
            })
        self.parameters["ue#cell"]["ru"]["tx_gain"] = ue_params["tx_gain"]
        self.parameters["ue#cell"]["ru"]["rx_gain"] = ue_params["rx_gain"]

    def check_ue_connect(self, nr, band, rf_mode, bandwidth=None, freq=None, enb_params={}, ue_cell_params={}, check={}):

        self.logger.info(f"Checking following configuration: 5G={nr}, {band}, {rf_mode}, {bandwidth}, {freq}")
        ue_params = self.setup_enb_gnb(nr, band, rf_mode, bandwidth,
                                       freq=freq, enb_params=enb_params, check=check)
        self.setup_ue(nr, rf_mode, ue_params, ue_cell_params)

        for ref in self.parameters:
          self.update_service(ref, "started", parameters=self.parameters[ref], lock=False)

        self.wait_until_ready(nr, ue_params['dl_nr_arfcn'] if nr else ue_params['dl_earfcn'])
        self.check_lteue_ip()

    def check_vonr_established(self, core_network_ue_list, ims_user_list, gnb_ue_list):
        if len(gnb_ue_list) != 1:
            self.logger.info(f"{len(gnb_ue_list)} UE are connected instead of 1")
            return False
        amf_ue_id = gnb_ue_list[0].get('amf_ue_id')
        found = False
        for ue in core_network_ue_list:
            if ue.get('amf_ue_id') == amf_ue_id:
                core_network_ue = ue
                break
        else:
            self.logger.info(f"{amf_ue_id} UE not in core network ue list")
            return False
        imsi = core_network_ue.get('imsi')
        for bearer in core_network_ue.get('bearers', []):
            if bearer.get('apn') == 'ims':
                break
        else:
            self.logger.info(f"No IMS APN found in {amf_ue_id} bearer list")
            return False
        for user in ims_user_list:
            if imsi in user.get('impi'):
                ims_user = user
                break
        else:
            self.logger.info(f"{imsi} not found in IMS user list IMPIs")
            return False
        if not ims_user.get('bindings'):
            self.logger.info(f"No active bindings for IMS user {imsi}")
            return False
        return True

    def check_error_handling(self, nr, invalid_enb_params, expected_error, error_key):
        # First setup a normal B38 or N41 config
        self.logger.info(f"Setup valid {'N41' if nr else 'B38'} configuration")
        self.setup_enb_gnb(nr, 'B38', 'TDD', check={"RADIO.band": "n41" if nr else "b38"})

        # Then, setup invalid B39 or N39 config
        self.logger.info("Setup invalid N39 configuration")
        self.config_enb_gnb(nr, 'B39', 'TDD', enb_params=invalid_enb_params)

        self.logger.info("Update eNB / gNB parameters")
        self.update_service("enb-gnb", "started", parameters=self.parameters["enb-gnb"], lock=False)

        self.logger.info("Waiting until parameters update")
        for i in range(30):
            time.sleep(10)
            connection_params = self.getInstanceInfos(self.enb_gnb_instance_name).connection_dict
            error = connection_params.get(error_key, '')
            if expected_error in error:
                self.logger.info(f'"{error}" contains "{expected_error}"')
                break
            self.logger.info(f'"{error}" does not contain "{expected_error}"')
        else:
            self.assertTrue(False, f'Connection Parameter {error_key} does not contain following expected error: "{expected_error}"')

        # Check that previous lteenb is still running with working N41 configuration
        try:
            self.setup_enb_websocket_connection()
            enb_cell = self.enb_config_get_cell()
            if nr:
                self.assertTrue(enb_cell['band'] == 41,
                  f'Previous configuration is not running anymore: {enb_cell["band"]} != 41')
            else:
                self.assertTrue(enb_cell['band'] == 38,
                  f'Previous configuration is not running anymore: {enb_cell["band"]} != 38')
        finally:
            self.close_enb_websocket_connection()

    def test_nr_B38_20_tdd1(self):
        tdd_config = "DDDDDDDSUU (5ms,   7DL/2UL), S-slot=6DL:4GP:4UL, default"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2601,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            })
    def test_nr_B38_20_tdd2(self):
        tdd_config = "DDDSUUDDDD (5ms,   7DL/2UL), S-slot=6DL:4GP:4UL, same ratios as default"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2602,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            })
    def test_nr_B38_20_tdd3(self):
        tdd_config = "DDDSUUUUDD (5ms,   5DL/4UL), S-slot=6DL:4GP:4UL, balanced downlink and uplink"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2603,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            })
    def test_nr_B38_20_tdd4(self):
        tdd_config = "DDDSUUUUUU (5ms,   3DL/6UL), S-slot=2DL:2GP:10UL, high uplink"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2604,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            })
    def test_nr_B38_20_tdd5(self):
        tdd_config = "DDSUUUUUUU (5ms,   2DL/7UL), S-slot=6DL:4GP:4UL, EXPERIMENTAL very high uplink"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2605,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            })
    def test_nr_B38_20_tdd6(self):
        tdd_config = "DSUUUUUUUU (5ms,   1DL/8UL), S-slot=10DL:2GP:2UL, EXPERIMENTAL maximum uplink"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2606,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            })
    def test_nr_B38_20_tdd7(self):
        tdd_config = "DDDSU      (2.5ms, 2DL/2UL), S-slot=6DL:4GP:4UL, reduced latency, balanced downlink and uplink"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2607,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            },
            ue_cell_params={"rx_to_tx_latency": 2})
    def test_nr_B38_20_tdd8(self):
        tdd_config = "DSUUU      (2.5ms, 1DL/3UL), S-slot=6DL:4GP:4UL, reduced latency, high uplink, no TRS"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2608,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            },
            ue_cell_params={"rx_to_tx_latency": 2})
    def test_nr_B38_20_tdd9(self):
        tdd_config = "DSUUU      (2.5ms, 1DL/3UL), S-slot=9DL:4GP:1UL, reduced latency, high uplink"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2609,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            },
            ue_cell_params={"rx_to_tx_latency": 2})
    def test_nr_B38_20_tdd10(self):
        tdd_config = "DS         (1ms, 1DL/0UL), S-slot=0DL:2GP:12UL, minimum latency, balanced downlink and uplink, no TRS"
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2610,
            enb_params={"cell1": {
                "tdd_ul_dl_config": tdd_config,
                "mcs_table_ul": "qam64",
                "mcs_table_dl": "qam64",
                }}, check={
                "RADIO.tdd-ul-dl-config": tdd_config
            },
            ue_cell_params={"rx_to_tx_latency": 3})

    def test_lte_B38_3(self):
        self.check_ue_connect(False, 'B38', 'TDD', 3, freq=2572)
    def test_lte_B38_5(self):
        self.check_ue_connect(False, 'B38', 'TDD', 5, freq=2573)
    def test_lte_B38_10(self):
        self.check_ue_connect(False, 'B38', 'TDD', 10, freq=2575)
    def test_lte_B38_15(self):
        self.check_ue_connect(False, 'B38', 'TDD', 15, freq=2578)
    def test_lte_B38_20(self):
        self.check_ue_connect(False, 'B38', 'TDD', 20, freq=2580)

    def test_nr_B28_5(self):
        self.check_ue_connect(True, 'B28', 'FDD', 5, freq=781)
    def test_nr_B38_10(self):
        self.check_ue_connect(True, 'B38', 'TDD', 10, freq=2575)
    def test_nr_B38_15(self):
        self.check_ue_connect(True, 'B38', 'TDD', 15, freq=2578)
    def test_nr_B38_20(self):
        self.check_ue_connect(True, 'B38', 'TDD', 20, freq=2581)
    def test_nr_B38_25(self):
        self.check_ue_connect(True, 'B38', 'TDD', 25, freq=2583)
    def test_nr_B38_30(self):
        self.check_ue_connect(True, 'B38', 'TDD', 30, freq=2585)
    def test_nr_B38_35(self):
        self.check_ue_connect(True, 'B38', 'TDD', 35, freq=2588)
    def test_nr_B38_40(self):
        self.check_ue_connect(True, 'B38', 'TDD', 40, freq=2590)
    def test_nr_B38_45(self):
        self.check_ue_connect(True, 'B38', 'TDD', 45, freq=2593)
    def test_nr_B38_50(self):
        self.check_ue_connect(True, 'B38', 'TDD', 50, freq=2595)

    def test_lte_B28(self):
        self.check_ue_connect(False, 'B28', 'FDD')
    def test_lte_B38(self):
        self.check_ue_connect(False, 'B38', 'TDD')
    def test_lte_B39(self):
        self.check_ue_connect(False, 'B39', 'TDD')
    def test_lte_B40(self):
        self.check_ue_connect(False, 'B40', 'TDD')
    def test_lte_B42(self):
        self.check_ue_connect(False, 'B42', 'TDD')
    def test_lte_B43(self):
        self.check_ue_connect(False, 'B43', 'TDD')
    def test_nr_B28(self):
        self.check_ue_connect(True, 'B28', 'FDD')
    def test_nr_B38(self):
        self.check_ue_connect(True, 'B38', 'TDD')
    def test_nr_B39(self):
        self.check_ue_connect(True, 'B39', 'TDD')
    def test_nr_B40(self):
        self.check_ue_connect(True, 'B40', 'TDD')
    def test_nr_N77(self):
        self.check_ue_connect(True, 'N77', 'TDD')
    def test_nr_B42(self):
        self.check_ue_connect(True, 'B42', 'TDD')
    def test_nr_B43(self):
        self.check_ue_connect(True, 'B43', 'TDD')
    def test_nr_N79(self):
        self.check_ue_connect(True, 'N79', 'TDD')

    def test_invalid_param_nr_n150(self):
        self.check_error_handling(
            True,
            {
                "cell1": {
                  "nr_band": 150,
                },
            },
            'n150 is not a valid NR band',
            '0-ERROR.BAND.cell1',
        )

    def test_invalid_param_nr_freq0(self):
        self.check_error_handling(
            True,
            {
                "cell1": {
                  "dl_frequency": 0,
                },
            },
            'band39: NR-ARFCN=0 is outside of downlink spectrum',
            '0-ERROR.CELL.cell1',
        )

    def test_invalid_param_nr_arfcn(self):
        self.check_error_handling(
            True,
            {
                "cell1": {
                  "dl_nr_arfcn": 380001,
                },
            },
            'the DL frequency must be a multiple of 100 kHz',
            '0-ERROR.amarisoft',
        )

    def test_invalid_param_lte_freq0(self):
        self.check_error_handling(
            False,
            {
                "cell1": {
                  "dl_frequency": 0,
                },
            },
            'B39 does not cover frequency=0 MHz',
            '0-ERROR.CELL.cell1',
        )


    def test_vonr(self):
        try:
            self.setup_adb_websocket_connection()
            self.adb_airplane_enable()
        finally:
            self.close_adb_websocket_connection()

        self.logger.info(f"Checking VoNR")

        self.config_enb_gnb(True, 'B39', 'TDD', bandwidth=20)

        rf_info = json.loads(self.parameters["enb-gnb"]["rf-info"])
        rf_info["sdr_map"]["0"]["sdr_dev"] = 6
        rf_info["sdr_map"]["1"]["sdr_dev"] = 7
        self.parameters["enb-gnb"]["rf-info"] = json.dumps(rf_info)

        self.parameters["enb-gnb"]["nodeb"]["plmn_list_5g"][0]["plmn"] = "00101"
        self.parameters["core-network#sim"]["plmn"] = "00101"
        self.parameters["core-network"]["core_network_plmn"] = "00101"

        ue_params = self.check_enb_gnb(True, 'B39', bandwidth=20, check_plmn="00101")

        self.parameters["enb-gnb"]["cell1"]["tx_gain"] = 90
        self.parameters["enb-gnb"]["cell1"]["rx_gain"] = 60

        for ref in self.parameters:
          self.update_service(ref, "started", parameters=self.parameters[ref], lock=False)

        self.wait_until_ready(True, ue_params['dl_nr_arfcn'], wait_ue=False, wait_core_network=True)

        retry = True

        success = False
        for i in range(MAX_RETRY):
            if not retry:
              break
            retry = False
            try:
                self.setup_core_network_websocket_connection()
                self.setup_ims_websocket_connection()
                self.setup_enb_websocket_connection()
                self.setup_adb_websocket_connection()
                self.adb_airplane_disable()
                time.sleep(1.5)
                for i in range(20):
                    time.sleep(0.1)
                    core_network_ue_list = self.core_network_ue_get()['ue_list']
                    ims_user_list = self.ims_ue_get()['users']
                    gnb_ue_list = self.enb_ue_get()['ue_list']
                    if self.check_vonr_established(core_network_ue_list, ims_user_list, gnb_ue_list):
                        success = True
                        break
                if success:
                    break
            except (_exceptions.WebSocketConnectionClosedException, _exceptions.WebSocketBadStatusException, json.decoder.JSONDecodeError):
                retry = True
            finally:
                self.adb_airplane_enable()
                self.close_core_network_websocket_connection()
                self.close_ims_websocket_connection()
                self.close_enb_websocket_connection()
                self.close_adb_websocket_connection()
        self.assertTrue(success, "VoNR check didn't pass")

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
