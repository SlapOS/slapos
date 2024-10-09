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

param_dict = {
    'testing': True,
    'tx_gain': 17,
    'rx_gain': 17,
    'pci': 250,
    'tac': '0x1717',
    'root_sequence_index': '1',
    'core_network_plmn': '00102',
    'rue_addr': '192.168.99.88',
    'n_antenna_dl': 2,
    'n_antenna_ul': 2,
    'inactivity_timer': 17,
    'ncell_list': {
        'ORS1': {
            'dl_earfcn': 40000,
            'dl_nr_arfcn': 403500,
            'ssb_nr_arfcn': 403500,
            'pci': 1,
            'nr_cell_id': '0x0000001',
            'cell_id': '0x0000001',
            'gnb_id_bits': 28,
            'nr_band': 34,
            'tac': 1
        },
        'ORS2': {
            'dl_earfcn': 50000,
            'dl_nr_arfcn': 519000,
            'ssb_nr_arfcn': 519000,
            'pci': 2,
            'nr_cell_id': '0x0000002',
            'cell_id': '0x0000001',
            'gnb_id_bits': 30,
            'nr_band': 38,
            'tac': 2
        },
    },
}
enb_param_dict = {
    # ors_version for tests is B39, so earfcn needs to be within B39
    'dl_earfcn': 38450,
    'enb_id': '0x17',
    'bandwidth': "10 MHz",
    'plmn_list': {
        '00101': {'attach_without_pdn': True, 'plmn': '00101', 'reserved': True},
        '00102': {'attach_without_pdn': False, 'plmn': '00102', 'reserved': False},
    },
    'tdd_ul_dl_config': '[Configuration 6] 5ms 5UL 3DL (maximum uplink)',
    'mme_list': {
        '10.0.0.1': {'mme_addr': '10.0.0.1'},
        '2001:db8::1': {'mme_addr': '2001:db8::1'},
    },
    'ncell_list': {
        'ORS1': {
            'dl_earfcn': 40000,
            'pci': 1,
            'cell_id': '0x0000001',
            'tac': 1
        },
        'ORS2': {
            'dl_earfcn': 50000,
            'pci': 2,
            'cell_id': '0x0000001',
            'tac': 2
        },
    },
}
gnb_param_dict = {
    # ors_version for tests is B39, so dl_nr_arfcn needs to be within N39
    'dl_nr_arfcn': 380000,
    'nr_band': 39,
    'nr_bandwidth': 40,
    'ssb_nr_arfcn': 380020,
    'gnb_id': '0x17',
    'gnb_id_bits': 30,
    'ssb_pos_bitmap': '10',
    'amf_list': {
        '10.0.0.1': {'amf_addr': '10.0.0.1'},
        '2001:db8::1': {'amf_addr': '2001:db8::1'},
    },
    'nr_handover_time_to_trigger': 40,
    'nr_handover_a3_offset': 10,
    'xn_peers': {
        '2001:db8::1': {
            'xn_addr': '2001:db8::1',
        },
        '2001:db8::2': {
            'xn_addr': '2001:db8::2',
        },
    },
    'ncell_list': {
        'ORS1': {
            'dl_nr_arfcn': 403500,
            'ssb_nr_arfcn': 403500,
            'pci': 1,
            'nr_cell_id': '0x0000001',
            'gnb_id_bits': 28,
            'nr_band': 34,
            'tac': 1
        },
        'ORS2': {
            'dl_nr_arfcn': 519000,
            'ssb_nr_arfcn': 519000,
            'pci': 2,
            'nr_cell_id': '0x0000002',
            'gnb_id_bits': 30,
            'nr_band': 38,
            'tac': 2
        },
    },
}
gnb_param_dict1 = {
    'plmn_list': {
        '00101': {'plmn': '00101', 'ranac': 1, 'reserved': True, 'tac': 1},
        '00102': {'plmn': '00102', 'ranac': 2, 'reserved': False, 'tac': 2},
    },
    'tdd_ul_dl_config': '2.5ms 1UL 3DL 2/10',
}
gnb_param_dict2 = {
    'nssai': {
        '0x171717': {'sd': '0x171717', 'sst': 10},
        '0x181818': {'sd': '0x181818', 'sst': 20},
    },
    'tdd_ul_dl_config': '5ms 6UL 3DL 10/2 (high uplink)',
}
enb_param_dict.update(param_dict)
gnb_param_dict1.update(gnb_param_dict)
gnb_param_dict1.update(param_dict)
gnb_param_dict2.update(gnb_param_dict)
gnb_param_dict2.update(param_dict)

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

    self.assertEqual(conf['tx_gain'], [enb_param_dict['tx_gain']] * enb_param_dict['n_antenna_dl'])
    self.assertEqual(conf['rx_gain'], [enb_param_dict['rx_gain']] * enb_param_dict['n_antenna_ul'])
    self.assertEqual(conf['cell_list'][0]['inactivity_timer'], enb_param_dict['inactivity_timer'])
    self.assertEqual(conf['cell_list'][0]['uldl_config'], 6)
    self.assertEqual(conf['cell_list'][0]['dl_earfcn'], enb_param_dict['dl_earfcn'])
    self.assertEqual(conf['cell_list'][0]['n_rb_dl'], 50)
    self.assertEqual(conf['enb_id'], int(enb_param_dict['enb_id'], 16))
    self.assertEqual(conf['cell_list'][0]['n_id_cell'], enb_param_dict['pci'])
    self.assertEqual(conf['cell_list'][0]['tac'], int(enb_param_dict['tac'], 16))
    self.assertEqual(conf['cell_list'][0]['root_sequence_index'], int(enb_param_dict['root_sequence_index']))
    self.assertEqual(conf['cell_list'][0]['cell_id'], 1)
    for p in conf['cell_default']['plmn_list']:
      for n in "plmn attach_without_pdn reserved".split():
        self.assertEqual(p[n], enb_param_dict['plmn_list'][p['plmn']][n])
    for p in conf['mme_list']:
      self.assertEqual(p['mme_addr'], enb_param_dict['mme_list'][p['mme_addr']]['mme_addr'])

    for p in conf['cell_list'][0]['ncell_list']:
      for k in enb_param_dict['ncell_list']:
        if p['dl_earfcn'] == gnb_param_dict1['ncell_list'][k]['dl_earfcn']:
          break
      conf_ncell = enb_param_dict['ncell_list'][k]
      self.assertEqual(p['dl_earfcn'],  conf_ncell['dl_earfcn'])
      self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
      self.assertEqual(p['cell_id'],   int(conf_ncell['cell_id'], 16))
      self.assertEqual(p['tac'],          conf_ncell['tac'])


class TestGNBParameters1(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(gnb_param_dict1)}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "gnb"
  def test_gnb_conf(self):

    conf = load_yaml_conf(self.slap, 'enb')

    self.assertEqual(conf['tx_gain'], [gnb_param_dict1['tx_gain']] * gnb_param_dict1['n_antenna_dl'])
    self.assertEqual(conf['rx_gain'], [gnb_param_dict1['rx_gain']] * gnb_param_dict1['n_antenna_ul'])
    self.assertEqual(conf['nr_cell_list'][0]['inactivity_timer'], gnb_param_dict1['inactivity_timer'])
    self.assertEqual(conf['nr_cell_list'][0]['dl_nr_arfcn'], gnb_param_dict1['dl_nr_arfcn'])
    self.assertEqual(conf['nr_cell_list'][0]['band'], gnb_param_dict1['nr_band'])
    self.assertEqual(conf['nr_cell_list'][0]['ssb_pos_bitmap'], gnb_param_dict1['ssb_pos_bitmap'])
    self.assertEqual(conf['nr_cell_list'][0]['bandwidth'], gnb_param_dict1['nr_bandwidth'])
    self.assertEqual(conf['nr_cell_list'][0]['n_id_cell'], gnb_param_dict1['pci'])
    self.assertEqual(conf['gnb_id'], int(gnb_param_dict1['gnb_id'], 16))
    self.assertEqual(conf['gnb_id_bits'], gnb_param_dict1['gnb_id_bits'])
    for p in conf['nr_cell_default']['plmn_list']:
      for n in "plmn ranac reserved tac".split():
        self.assertEqual(p[n], gnb_param_dict1['plmn_list'][p['plmn']][n])
    for p in conf['amf_list']:
      self.assertEqual(p['amf_addr'], gnb_param_dict1['amf_list'][p['amf_addr']]['amf_addr'])
    for p in conf['xn_peers']:
      self.assertEqual(p, gnb_param_dict1['xn_peers'][p]['xn_addr'])
    for p in conf['nr_cell_list'][0]['ncell_list']:
      for k in gnb_param_dict1['ncell_list']:
        if p['dl_nr_arfcn'] == gnb_param_dict1['ncell_list'][k]['dl_nr_arfcn']:
          break
      conf_ncell = gnb_param_dict1['ncell_list'][k]
      self.assertEqual(p['dl_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])
      self.assertEqual(p['ssb_nr_arfcn'], conf_ncell['ssb_nr_arfcn'])
      self.assertEqual(p['ul_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])    # assumes nr_band is TDD
      self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
      self.assertEqual(p['gnb_id_bits'],  conf_ncell['gnb_id_bits'])
      self.assertEqual(p['nr_cell_id'],   int(conf_ncell['nr_cell_id'], 16))
      self.assertEqual(p['tac'],          conf_ncell['tac'])
      self.assertEqual(p['band'],         conf_ncell['nr_band'])
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
      self.assertEqual(sd, gnb_param_dict2['nssai'][sd]['sd'], 16)
      self.assertEqual(p['sst'], gnb_param_dict2['nssai'][sd]['sst'])

    tdd_config = conf['nr_cell_list'][0]['tdd_ul_dl_config']['pattern1']
    self.assertEqual(float(tdd_config['period']), 5)
    self.assertEqual(int(tdd_config['dl_slots']), 3)
    self.assertEqual(int(tdd_config['dl_symbols']), 2)
    self.assertEqual(int(tdd_config['ul_slots']), 6)
    self.assertEqual(int(tdd_config['ul_symbols']), 10)


class TestCoreNetworkParameters(ORSTestCase):
  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(param_dict)}
  @classmethod
  def getInstanceSoftwareType(cls):
    return "core-network"
  def test_mme_conf(self):

    conf = load_yaml_conf(self.slap, 'mme')

    self.assertEqual(conf['plmn'], param_dict['core_network_plmn'])

def test_monitor_gadget_url(self):
  parameters = json.loads(self.computer_partition.getConnectionParameterDict()['_'])
  self.assertIn('monitor-gadget-url', parameters)
  monitor_setup_url = parameters['monitor-setup-url']
  monitor_gadget_url = parameters['monitor-gadget-url']
  monitor_base_url = parameters['monitor-base-url']
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
    return {'_': json.dumps({'testing': True, 'slave-list': []})}

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
    return {'_': json.dumps({'testing': True, 'fixed_ips': cls.fixed_ips})}
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
