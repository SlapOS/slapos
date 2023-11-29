import e2e

class ORSTest(e2e.WebsocketTestClass):
  # instance_name = time.strftime('e2e-test-kvm-%Y-%B-%d-%H:%M:%S')
  instance_name = 'cb006-enb' # avoid timestamp to reuse instance
  ors_sr_url = "https://lab.nexedi.com/nexedi/slapos/raw/ors-oran-ru/software/ors-amarisoft/software-fdd-lopcomm.cfg"
  ws_url = "ws://[2a11:9ac0:d::1]:9002"
  final_state = 'started'

  @classmethod
  def setUpClass(cls):

    super().setUpClass(ws_url=cls.ws_url)
    cls.common_setup()
    cls.waitUntilGreen(cls.instance_name)
    connection_dict = cls.getInstanceInfos(cls.instance_name).connection_dict

#    parser = argparse.ArgumentParser(description='Connect to a lteue websocket to perform some testing.')
#    parser.add_argument('url', help='url of the websocket in the form ws://[XXX]:XXX (eg "ws://[2a11:9ac0:d::1]:9002")')
#    args = parser.parse_args()

    #self.ws_url = "ws://[2a11:9ac0:d::1]:9002"
    #cls.ws_url = "ws://[2a11:9ac0:d::df82]:9002"
    #self.ws = create_connection(self.ws_url)
    # self.test_ue_has_ip()

  def test_ors_promise_feed(self):
    resp, url = self.waitUntilMonitorURLReady(instance_name=self.instance_name)
    self.getMonitorPromises(resp.content)

  def test_ue_has_ip(self):
      self.common_setup(txa0cc00_active="ACTIVE", rxa0cc00_active="ACTIVE")
      self.waitUntilGreen(self.instance_name)
      result = self.recv()
      result = self.ue_get()
      ue_id = result['ue_id']

      try:
          self.power_on(ue_id)
          e2e.time.sleep(2)
          result = self.ue_get()
          self.assertIn('pdn_list', result, "UE didn't connect")
          self.assertIn('ipv4', result['pdn_list'][0], "UE didn't get IPv4")
          print("UE connected with ip: " + result['pdn_list'][0]['ipv4'])
      finally:
          self.power_off(ue_id)

  def test_ue_disconnected_when_carrier_inactive(self):
    self.common_setup(txa0cc00_active="INACTIVE", rxa0cc00_active="INACTIVE")
    self.waitUntilGreen(self.instance_name)
    try:
        # Ensure the UE is disconnected
        result = self.ue_get()
        if 'power_on' in result:
            self.assertFalse(result['power_on'], "UE can't be powered on when inactive")
    except Exception as e:
        self.fail(str(e))

  def test_baseband_latency(self):
    self.common_setup(min_rxtx_delay=99)
    self.waitUntilPromises(self.instance_name, promise_name="check-baseband-latency", expected=False)

  @classmethod
  def common_setup(cls, txa0cc00_active="ACTIVE", rxa0cc00_active="ACTIVE", min_rxtx_delay=0):
      instance_name = cls.instance_name
      ors_sr_url = cls.ors_sr_url
      parameter_dict = {
          "bandwidth": "20 MHz",
          "n_antenna_dl": 1,
          "n_antenna_ul": 1,
          "cpri_mult": 16,
          "cell_list": {
              "RRH-B1": {
                  "cpri_rx_delay": 25.11,
                  "cpri_tx_delay": 14.71,
                  "cpri_tx_dbm": 63,
                  "ru_mac_addr": "00:0a:00:00:10:20",
                  "dl_earfcn": 300
              }
          },
          "dnsmasq": True,
          "txa0cc00_active": txa0cc00_active,
          "rxa0cc00_active": rxa0cc00_active,
          "txa0cc00_center_frequency": 2140,
          "rxa0cc00_center_frequency_earfcn": 18300,
          "rxa0cc00_center_frequency": 1950,
          "txa0cc00_gain": -20,
          "user-authorized-key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDegkDlZaDJEoiXo5FZ5iJmYcVHyqd5G+YaWLmZ/Ae6wtY8Pp0e/+eCcARO67pwn73MAj9IELu3h5rdPuZvZx0xXWGOc3ceOQBsJh/h4eMpiBKvA5ELWVuXDIl98xgIIjiaO4QgZyw1OhpN5EB6EyUNKt/xCHuU37mZaFLbcNDW3h6JI5U5plIARY0e/dFPFywtKqCgnqhJubJh/kHcb4ZeJzQMnA33WGwVD/b+F015kHXfk4T259Z27yqMTokVjaiUnI2Wbac3e+Lc5bpecA68rlmhc6fs0bh5Geldy2Q8y8gJQUX3sihA9PjlDN+T8mNYHyk9QaCM/SQkwxB71D172nMoUcrppUZyf6JaLmB/cO0iVsIr8x2GnGT0EzL/y1hmvi1dD17E0DpgoRcjI3DxleTbUTpayT4ZHrtVnkp2Nf1LgEJmdTx0hqTb9HTqhXATTKLSETYAwIu0yWnlA9oK2MwsiPPQ/8IS5HzhN3XFEIdV+tQ7GZPVfv4sYpwt7us= root@root",
          "plmn_list": {
              "Australia": {
                  "plmn": "50501"
              }
          },
          "min_rxtx_delay": min_rxtx_delay,
        }
      json_in_xml_parameters = {'_': e2e.json.dumps(parameter_dict)}
      cls.request(
          ors_sr_url,
          instance_name,
          partition_parameter_kw=json_in_xml_parameters,
          software_type='enb'
      )
      e2e.time.sleep(300)
