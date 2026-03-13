##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import json
import glob
import requests
import netaddr

from test import yamlpp_load

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, ORSTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software-ors.cfg')))

core_network_param_dict = {
    'testing': True,
    'lte_mock': True,
    'core_network_plmn': '00102',
}
rf_info = {
    "sdr_map": {
      "0": {
        "serial": "B0",
        "version": "4.2",
        "band": "B39",
        "tdd": "TDD",
        "model": "ORS"
      },
    },
    "flavour": "ORS"
}
param_dict = {
    'testing': True,
    'lte_mock': True,
    'rf-info': json.dumps(rf_info),
    'cell1': {
        'tx_gain': 17,
        'rx_gain': 18,
        'tx_power_offset': 19,
        'cell_id': '0x01',
        'pci': 250,
        'root_sequence_index': 1,
    },
    'nodeb': {
        'n_antenna_dl': 2,
        'n_antenna_ul': 2,
        'inactivity_timer': 17,
        'ncell_list': [
            {
                'name': 'ORS1',
                'cell_type': 'lte',
                'cell_kind': 'enb_peer',
                'dl_earfcn': 38450,
                'pci': 1,
                'e_cell_id': '0x0000001',
                'tac': '0x01',
                'plmn': "00101"
            },
            {
                'name': 'ORS2',
                'cell_type': 'lte',
                'cell_kind': 'enb_peer',
                'dl_earfcn': 38050,
                'pci': 2,
                'e_cell_id': '0x0000002',
                'tac': '0x01',
                'plmn': "00101"
            },
            {
                'name': 'ORS3',
                'cell_type': 'nr',
                'cell_kind': 'enb_peer',
                'dl_nr_arfcn': 519000,
                'ssb_nr_arfcn': 518910,
                'ul_nr_arfcn': 519000,
                'pci': 1,
                'nr_cell_id': '0x0000001',
                'gnb_id_bits': 28,
                'nr_band': 41,
                'tac': '0x01',
                'plmn': "00101"
            },
            {
                'name': 'ORS4',
                'cell_type': 'nr',
                'cell_kind': 'enb_peer',
                'dl_nr_arfcn': 378000,
                'ssb_nr_arfcn': 378030,
                'ul_nr_arfcn': 378000,
                'pci': 2,
                'nr_cell_id': '0x0000002',
                'gnb_id_bits': 30,
                'nr_band': 39,
                'tac': '0x02',
                'plmn': "00101"
            },
        ],
    },
}
enb_param_dict = {
    'cell1': {
        # ors_version for tests is B39, so earfcn needs to be within B39
        'tac': '0x1717',
        'dl_earfcn': 38450,
        'bandwidth': "10 MHz",
        'tdd_ul_dl_config': '[Configuration 4] DSUUDDDDDD (10ms, 7DL/2UL), S-slot=10DL:2GP:2UL, high downlink',
    },
    'nodeb': {
        'enb_id': '0x17',
        'plmn_list': [
            {'attach_without_pdn': True, 'plmn': '00101', 'reserved': True},
            {'attach_without_pdn': False, 'plmn': '00102', 'reserved': False},
        ],
        'mme_list': [
            {'name': '10.0.0.1',    'mme_addr': '10.0.0.1'},
            {'name': '2001:db8::1', 'mme_addr': '2001:db8::1'},
        ],
    },
    'management': {
        'xlog_forwarding_enabled': False,
        'check_core_network': False,
    },
}
gnb_param_dict = {
    'cell1': {
        # ors_version for tests is B39, so dl_nr_arfcn needs to be within N39
        'dl_nr_arfcn': 378000,
        'nr_band': 39,
        'nr_bandwidth': 40,
        'ssb_nr_arfcn': 378030,
        'ssb_pos_bitmap': '10',
    },
    'nodeb': {
        'gnb_id': '0x17',
        'gnb_id_bits': 30,
        'amf_list': [
            {'name': '10.0.0.1',    'amf_addr': '10.0.0.1'},
            {'name': '2001:db8::1', 'amf_addr': '2001:db8::1'},
        ],
        'xn_peers': [
            {
                'name': '2001:db8::1',
                'xn_addr': '2001:db8::1',
            },
            {
                'name': '2001:db8::2',
                'xn_addr': '2001:db8::2',
            },
        ],
    },
    'management': {
        'xlog_forwarding_enabled': False,
        'check_core_network': False,
    },
}
gnb_param_dict1 = {
    'cell1': {
        'tdd_ul_dl_config': 'DDDSU      (2.5ms, 3DL/1UL), S-slot=10DL:2GP:2UL, reduced latency',
    },
    'nodeb': {
        'plmn_list': [
            {'plmn': '00101', 'ranac': 1, 'reserved': True, 'tac': '0x01'},
            {'plmn': '00102', 'ranac': 2, 'reserved': False, 'tac': '0x02'},
        ],
    },
}
gnb_param_dict2 = {
    'cell1': {
        'tdd_ul_dl_config': 'DDDSUUUUUU (5ms,   3DL/6UL), S-slot=2DL:2GP:10UL, high uplink',
    },
    'nodeb': {
        'nssai': [
            {'sd': '0x171717', 'sst': 10},
            {'sd': '0x181818', 'sst': 20},
        ],
    },
}

for k in param_dict:
  if k in "cell1 nodeb management".split(" "):
    enb_param_dict.setdefault(k,  {}).update(param_dict[k])
    gnb_param_dict1.setdefault(k, {}).update(param_dict[k])
    gnb_param_dict2.setdefault(k, {}).update(param_dict[k])
  else:
    enb_param_dict[k]  = param_dict[k]
    gnb_param_dict1[k] = param_dict[k]
    gnb_param_dict2[k] = param_dict[k]

for s in "cell1 nodeb management".split(" "):
    gnb_param_dict1.setdefault(s, {}).update(gnb_param_dict.get(s, {}))
    gnb_param_dict2.setdefault(s, {}).update(gnb_param_dict.get(s, {}))

for d in [enb_param_dict, gnb_param_dict1, gnb_param_dict2]:
    d['testing']  = True
    d['lte_mock'] = True

def load_yaml_conf(slap, name):
    conf_file = glob.glob(os.path.join(
      slap.instance_directory, '*', 'etc', name + '.cfg'))[0]
    return yamlpp_load(conf_file)

class TestENBParameters(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(enb_param_dict)}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "enb"
  def test_enb_conf(self):

    conf = load_yaml_conf(self.slap, 'enb')

    self.assertEqual(conf['tx_gain'], [enb_param_dict['cell1']['tx_gain']] * enb_param_dict['nodeb']['n_antenna_dl'])
    self.assertEqual(conf['rx_gain'], [enb_param_dict['cell1']['rx_gain']] * enb_param_dict['nodeb']['n_antenna_ul'])
    self.assertEqual(conf['rf_ports'][0]['tx_power_offset'], enb_param_dict['cell1']['tx_power_offset'])
    self.assertEqual(conf['cell_list'][0]['inactivity_timer'], enb_param_dict['nodeb']['inactivity_timer'])
    self.assertEqual(conf['cell_list'][0]['uldl_config'], 4)
    self.assertEqual(conf['cell_list'][0]['dl_earfcn'], enb_param_dict['cell1']['dl_earfcn'])
    self.assertEqual(conf['cell_list'][0]['n_rb_dl'], 50)
    self.assertEqual(conf['enb_id'], int(enb_param_dict['nodeb']['enb_id'], 16))
    self.assertEqual(conf['cell_list'][0]['n_id_cell'], enb_param_dict['cell1']['pci'])
    self.assertEqual(conf['cell_list'][0]['tac'], int(enb_param_dict['cell1']['tac'], 16))
    self.assertEqual(conf['cell_list'][0]['root_sequence_index'], enb_param_dict['cell1']['root_sequence_index'])
    self.assertEqual(conf['cell_list'][0]['cell_id'], 1)
    for p in conf['cell_default']['plmn_list']:
      for plmn in enb_param_dict['nodeb']['plmn_list']:
          if plmn['plmn'] == p['plmn']:
              break
      for n in "plmn attach_without_pdn reserved".split():
        self.assertEqual(p[n], plmn[n])
    for p in conf['mme_list']:
      for mme in enb_param_dict['nodeb']['mme_list']:
          if mme['name'] == p['mme_addr']:
              break
      self.assertEqual(p['mme_addr'], mme['mme_addr'])

    for p in conf['cell_list'][0]['ncell_list']:
      for ncell in param_dict['nodeb']['ncell_list']:
        if 'dl_earfcn' in p:
          if p['dl_earfcn'] == ncell.get('dl_earfcn', 0):
            break
        elif 'dl_nr_arfcn' in p:
          if p['dl_nr_arfcn'] == ncell.get('dl_nr_arfcn', 0):
            break
      conf_ncell = ncell
      if 'dl_earfcn' in p:
        self.assertEqual(p['dl_earfcn'],  conf_ncell['dl_earfcn'])
        self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
        self.assertEqual(p['tac'],          int(conf_ncell['tac'], 16))
        self.assertEqual(p['plmn'],          conf_ncell['plmn'])
      elif 'dl_nr_arfcn' in p:
        self.assertEqual(p['dl_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])
        self.assertEqual(p['ssb_nr_arfcn'], conf_ncell['ssb_nr_arfcn'])
        self.assertEqual(p['ul_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])    # assumes nr_band is TDD
        self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
        self.assertEqual(p['gnb_id_bits'],  conf_ncell['gnb_id_bits'])
        self.assertEqual(p['nr_cell_id'],   int(conf_ncell['nr_cell_id'], 16))
        self.assertEqual(p['tac'],          int(conf_ncell['tac'], 16))
        self.assertEqual(p['band'],         conf_ncell['nr_band'])
        self.assertEqual(p['plmn'],          conf_ncell['plmn'])


class TestGNBParameters1(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(gnb_param_dict1)}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "gnb"
  def test_gnb_conf(self):

    conf = load_yaml_conf(self.slap, 'enb')

    self.assertEqual(conf['tx_gain'], [gnb_param_dict1['cell1']['tx_gain']] * gnb_param_dict1['nodeb']['n_antenna_dl'])
    self.assertEqual(conf['rx_gain'], [gnb_param_dict1['cell1']['rx_gain']] * gnb_param_dict1['nodeb']['n_antenna_ul'])
    self.assertEqual(conf['nr_cell_list'][0]['inactivity_timer'], gnb_param_dict1['nodeb']['inactivity_timer'])
    self.assertEqual(conf['nr_cell_list'][0]['dl_nr_arfcn'], gnb_param_dict1['cell1']['dl_nr_arfcn'])
    self.assertEqual(conf['nr_cell_list'][0]['ssb_nr_arfcn'], gnb_param_dict1['cell1']['ssb_nr_arfcn'])
    self.assertEqual(conf['nr_cell_list'][0]['band'], gnb_param_dict1['cell1']['nr_band'])
    self.assertEqual(conf['nr_cell_list'][0]['ssb_pos_bitmap'], gnb_param_dict1['cell1']['ssb_pos_bitmap'])
    self.assertEqual(conf['nr_cell_list'][0]['bandwidth'], gnb_param_dict1['cell1']['nr_bandwidth'])
    self.assertEqual(conf['nr_cell_list'][0]['n_id_cell'], gnb_param_dict1['cell1']['pci'])
    self.assertEqual(conf['gnb_id'], int(gnb_param_dict1['nodeb']['gnb_id'], 16))
    self.assertEqual(conf['gnb_id_bits'], gnb_param_dict1['nodeb']['gnb_id_bits'])
    for p in conf['nr_cell_default']['plmn_list']:
      for plmn in gnb_param_dict1['nodeb']['plmn_list']:
          if plmn['plmn'] == p['plmn']:
              break
      for n in "plmn ranac reserved".split():
        self.assertEqual(p[n], plmn[n])
      self.assertEqual(int(p["tac"]), int(plmn["tac"], 16))
    for p in conf['amf_list']:
      for amf in gnb_param_dict1['nodeb']['amf_list']:
          if amf['name'] == p['amf_addr']:
              break
      self.assertEqual(p['amf_addr'], amf['amf_addr'])
    for p in conf['xn_peers']:
      for xn in gnb_param_dict1['nodeb']['xn_peers']:
        if xn['name'] == p:
            break
      self.assertEqual(p, xn['xn_addr'])

    for p in conf['nr_cell_list'][0]['ncell_list']:
      for ncell in param_dict['nodeb']['ncell_list']:
        if 'dl_earfcn' in p:
          if p['dl_earfcn'] == ncell.get('dl_earfcn', 0):
            break
        elif 'dl_nr_arfcn' in p:
          if p['dl_nr_arfcn'] == ncell.get('dl_nr_arfcn', 0):
            break
      conf_ncell = ncell
      if 'dl_earfcn' in p:
        self.assertEqual(p['dl_earfcn'],  conf_ncell['dl_earfcn'])
        self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
        self.assertEqual(p['tac'],          int(conf_ncell['tac'], 16))
        self.assertEqual(p['plmn'],          conf_ncell['plmn'])
      elif 'dl_nr_arfcn' in p:
        self.assertEqual(p['dl_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])
        self.assertEqual(p['ssb_nr_arfcn'], conf_ncell['ssb_nr_arfcn'])
        self.assertEqual(p['ul_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])    # assumes nr_band is TDD
        self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
        self.assertEqual(p['gnb_id_bits'],  conf_ncell['gnb_id_bits'])
        self.assertEqual(p['nr_cell_id'],   int(conf_ncell['nr_cell_id'], 16))
        self.assertEqual(p['tac'],          int(conf_ncell['tac'], 16))
        self.assertEqual(p['band'],         conf_ncell['nr_band'])
        self.assertEqual(p['plmn'],          conf_ncell['plmn'])

    tdd_config = conf['nr_cell_list'][0]['tdd_ul_dl_config']['pattern1']

    self.assertEqual(float(tdd_config['period']), 2.5)
    self.assertEqual(int(tdd_config['dl_slots']), 3)
    self.assertEqual(int(tdd_config['dl_symbols']), 10)
    self.assertEqual(int(tdd_config['ul_slots']), 1)
    self.assertEqual(int(tdd_config['ul_symbols']), 2)


class TestGNBParameters2(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(gnb_param_dict2)}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "gnb"
  def test_gnb_conf(self):

    conf = load_yaml_conf(self.slap, 'enb')

    for p in conf['nr_cell_default']['plmn_list'][0]['nssai']:
      sd = hex(p['sd'])
      for nssai in gnb_param_dict2['nodeb']['nssai']:
          if nssai['sd'] == sd:
              break
      self.assertEqual(sd, nssai['sd'], 16)
      self.assertEqual(p['sst'], nssai['sst'])

    tdd_config = conf['nr_cell_list'][0]['tdd_ul_dl_config']['pattern1']
    self.assertEqual(float(tdd_config['period']), 5)
    self.assertEqual(int(tdd_config['dl_slots']), 3)
    self.assertEqual(int(tdd_config['dl_symbols']), 2)
    self.assertEqual(int(tdd_config['ul_slots']), 6)
    self.assertEqual(int(tdd_config['ul_symbols']), 10)


class TestCoreNetworkParameters(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(core_network_param_dict)}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "core-network"
  def test_mme_conf(self):

    conf = load_yaml_conf(self.slap, 'mme')

    self.assertEqual(conf['plmn'], core_network_param_dict['core_network_plmn'])

def test_monitor_gadget_url(self):
  parameters = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
  self.assertIn('URL.monitor-gadget', parameters)
  monitor_setup_url = parameters['URL.monitor-setup']
  monitor_gadget_url = parameters['URL.monitor-gadget']
  monitor_base_url = parameters['URL.monitor-base']
  public_url = monitor_base_url + '/public'
  response = requests.get(public_url, verify=False)
  self.assertEqual(requests.codes['OK'], response.status_code)
  self.assertIn('software.cfg.html', monitor_gadget_url)
  response = requests.get(monitor_gadget_url, verify=False)
  self.assertEqual(requests.codes['OK'], response.status_code)
  self.assertIn('<script src="rsvp.js"></script>', response.text)
  self.assertIn('<script src="renderjs.js"></script>', response.text)
  self.assertIn('<script src="g-chart.line.js"></script>', response.text)
  self.assertIn('<script src="promise.gadget.js"></script>', response.text)


class TestENBMonitorGadgetUrl(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(enb_param_dict)}

  @classmethod
  def getInstanceSoftwareType(cls):
    return "enb"

  def test_monitor_gadget_url(self):
    test_monitor_gadget_url(self)

class TestGNBMonitorGadgetUrl(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(gnb_param_dict1)}

  @classmethod
  def getInstanceSoftwareType(cls):
    return "gnb"

  def test_monitor_gadget_url(self):
    test_monitor_gadget_url(self)

class TestCoreNetworkMonitorGadgetUrl(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'testing': True,
      'lte_mock': True,
      'slave-list': []
    })}

  @classmethod
  def getInstanceSoftwareType(cls):
    return "core-network"

  def test_monitor_gadget_url(self):
    test_monitor_gadget_url(self)

class TestSimCard(ORSTestCase):
  nb_sim_cards = 1
  fixed_ips = False
  tun_network = netaddr.IPNetwork('192.168.10.0/24')

  @classmethod
  def getSimParam(cls, id=0):
    return {
      'sim_algo': 'milenage',
      'imsi': '{0:015}'.format(1010000000000 + id),
      'opc': '000102030405060708090A0B0C0D0E0F',
      'amf': '0x9001',
      'sqn': '000000000000',
      'k': '00112233445566778899AABBCCDDEEFF',
      'impu': 'impu%s' % '{0:03}'.format(id),
      'impi': 'impi%s@amarisoft.com' % '{0:03}'.format(id)
    }

  @classmethod
  def requestDefaultInstance(cls, state='started'):

    default_instance = super(
        ORSTestCase, cls).requestDefaultInstance(state=state)
    cls._updateSlaposResource(
      os.path.join(
        cls.slap._instance_root, default_instance.getId()),
      tun={"ipv4_network": str(cls.tun_network)}
    )
    cls.requestSlaveInstance()
    return default_instance
  @classmethod
  def requestSlaveInstance(cls):
    for i in range(cls.nb_sim_cards):
      cls.requestSlaveInstanceWithId(i)
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
      'testing': True,
      'lte_mock': True,
      'fixed_ips': cls.fixed_ips
    })}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "core-network"
  @classmethod
  def requestSlaveInstanceWithId(cls, id=0):
    software_url = cls.getSoftwareURL()
    param_dict = cls.getSimParam(id)
    return cls.slap.request(
        software_release=software_url,
        partition_reference="SIM-CARD-%s" % id,
        partition_parameter_kw={'_': json.dumps(param_dict)},
        shared=True,
        software_type='core-network',
    )
  @classmethod
  def _updateSlaposResource(cls, partition_path, **kw):
    # we can update the .slapos-resourcefile from top partition because buildout
    # will search for a .slapos-resource in upper directories until it finds one
    with open(os.path.join(partition_path, '.slapos-resource'), 'r+') as f:
      resource = json.load(f)
      resource.update(kw)
      f.seek(0)
      f.truncate()
      json.dump(resource, f, indent=2)

  def test_sim_card(self):

    conf = load_yaml_conf(self.slap, 'ue_db')

    first_ip = netaddr.IPAddress(self.tun_network.first)
    for i in range(self.nb_sim_cards):
      params = self.getSimParam(i)
      for n in "sim_algo imsi opc sqn impu impi".split():
        self.assertEqual(conf['ue_db'][i][n], params[n], "%s doesn't match" % n)
      self.assertEqual(conf['ue_db'][i]['K'], params['k'])
      self.assertEqual(conf['ue_db'][i]['amf'], int(params['amf'], 16))

      p = self.requestSlaveInstanceWithId(i).getConnectionParameterDict()
      p = json.loads(p['_'])
      self.assertIn('info', p)
      if self.fixed_ips:
        self.assertIn('ipv4', p)
        if self.nb_sim_cards + 2 > self.tun_network.size:
          self.assertEqual(p['ipv4'], "Too many SIM for the IPv4 network")
        else:
          ip = str(first_ip + 2 + i)
          self.assertEqual(p['ipv4'], ip)
          self.assertEqual(conf['ue_db'][i]['pdn_list'][0]['access_point_name'], "internet")
          self.assertTrue(conf['ue_db'][i]['pdn_list'][0]['default'])
          self.assertEqual(conf['ue_db'][i]['pdn_list'][0]['ipv4_addr'], ip)


class TestSimCardManySim(TestSimCard):
  nb_sim_cards = 10

class TestSimCardFixedIps(TestSimCard):
  fixed_ips = True

class TestSimCardManySimFixedIps(TestSimCard):
  nb_sim_cards = 10
  fixed_ips = True

class TestSimCardTooManySimFixedIps(TestSimCard):
  nb_sim_cards = 10
  fixed_ips = True
  tun_network = netaddr.IPNetwork("192.168.10.0/29")
