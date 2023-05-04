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
import yaml
import json
import glob
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, ORSTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software-tdd3700.cfg')))

param_dict = {
    'testing': True,
    'sim_algo': 'milenage',
    'imsi': '001010000000331',
    'opc': '000102030405060708090A0B0C0D0E0F',
    'amf': '0x9001',
    'sqn': '000000000000',
    'k': '00112233445566778899AABBCCDDEEFF',
    'impu': 'impu331',
    'impi': 'impi331@amarisoft.com',
    'tx_gain': 17,
    'rx_gain': 17,
    'dl_earfcn': 325320,
    'n_rb_dl': 50,
    'enb_id': '0x17',
    'pci': 250,
    'mme_list': {
        '10.0.0.1': {'mme_addr': '10.0.0.1'},
        '2001:db8::1': {'mme_addr': '2001:db8::1'},
    },
    'core_network_plmn': '00102',
    'dl_nr_arfcn': 325320,
    'nr_band': 99,
    'nr_bandwidth': 50,
    'ssb_nr_arfcn': 377790,
    'rue_addr': '192.168.99.88',
    'n_antenna_dl': 2,
    'n_antenna_ul': 2,
    'inactivity_timer': 17,
    'gnb_id': '0x17',
    'gnb_id_bits': 30,
    'ssb_pos_bitmap': '10',
    'amf_list': {
        '10.0.0.1': {'amf_addr': '10.0.0.1'},
        '2001:db8::1': {'amf_addr': '2001:db8::1'},
    },
    'nr_handover_time_to_trigger': 50,
    'nr_handover_a3_offset': 10,
    'ncell_list': {
        'ORS1': {
            'dl_nr_arfcn': 100000,
            'ssb_nr_arfcn': 100000,
            'pci': 1,
            'nr_cell_id': '0x0000001',
            'gnb_id_bits': 28,
            'nr_band': 1,
            'tac': 1
        },
        'ORS2': {
            'dl_nr_arfcn': 200000,
            'ssb_nr_arfcn': 200000,
            'pci': 2,
            'nr_cell_id': '0x0000002',
            'gnb_id_bits': 30,
            'nr_band': 2,
            'tac': 2
        },
    },
    'xn_peers': {
        '2001:db8::1': {
            'xn_addr': '2001:db8::1',
        },
        '2001:db8::2': {
            'xn_addr': '2001:db8::2',
        },
    },
    'tdd_ul_dl_config': '2.5ms 1UL 3DL 2/10',
}
enb_param_dict = {
    'plmn_list': {
        '00101': {'attach_without_pdn': True, 'plmn': '00101', 'reserved': True},
        '00102': {'attach_without_pdn': False, 'plmn': '00102', 'reserved': False},
    },
}
gnb_param_dict1 = {
    'plmn_list': {
        '00101': {'plmn': '00101', 'ranac': 1, 'reserved': True, 'tac': 1},
        '00102': {'plmn': '00102', 'ranac': 2, 'reserved': False, 'tac': 2},
    },
}
gnb_param_dict2 = {
    'nssai': {
        '1': {'sd': 1, 'sst': 10},
        '2': {'sd': 2, 'sst': 20},
    },
}
enb_param_dict.update(param_dict)
gnb_param_dict1.update(param_dict)
gnb_param_dict2.update(param_dict)

def test_enb_conf(self):

    conf_file = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'etc', 'enb.cfg'))[0]

    with open(conf_file, 'r') as f:
        conf = yaml.load(f)
    self.assertEqual(conf['tx_gain'], enb_param_dict['tx_gain'])
    self.assertEqual(conf['rx_gain'], enb_param_dict['rx_gain'])
    self.assertEqual(conf['cell_default']['inactivity_timer'], enb_param_dict['inactivity_timer'])
    self.assertEqual(conf['cell_list'][0]['dl_earfcn'], enb_param_dict['dl_earfcn'])
    self.assertEqual(conf['enb_id'], int(enb_param_dict['enb_id'], 16))
    self.assertEqual(conf['cell_list'][0]['n_id_cell'], enb_param_dict['pci'])
    for p in conf['cell_list'][0]['plmn_list']:
      for n in "plmn attach_without_pdn reserved".split():
          self.assertEqual(p[n], enb_param_dict['plmn_list'][p['plmn']][n])
    for p in conf['mme_list']:
      self.assertEqual(p['mme_addr'], enb_param_dict['mme_list'][p['mme_addr']]['mme_addr'])

    with open(conf_file, 'r') as f:
        for l in f:
            if l.startswith('#define N_RB_DL'):
                self.assertIn(str(enb_param_dict['n_rb_dl']), l)

def test_gnb_conf1(self):

        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'gnb.cfg'))[0]

        with open(conf_file, 'r') as f:
            conf = yaml.load(f)
        self.assertEqual(conf['tx_gain'], gnb_param_dict1['tx_gain'])
        self.assertEqual(conf['rx_gain'], gnb_param_dict1['rx_gain'])
        self.assertEqual(conf['nr_cell_default']['inactivity_timer'], gnb_param_dict1['inactivity_timer'])
        self.assertEqual(conf['nr_cell_list'][0]['dl_nr_arfcn'], gnb_param_dict1['dl_nr_arfcn'])
        self.assertEqual(conf['nr_cell_list'][0]['band'], gnb_param_dict1['nr_band'])
        self.assertEqual(conf['nr_cell_list'][0]['ssb_pos_bitmap'], gnb_param_dict1['ssb_pos_bitmap'])
        self.assertEqual(conf['nr_cell_default']['n_id_cell'], gnb_param_dict1['pci'])
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
          self.assertEqual(p['ul_nr_arfcn'],  conf_ncell['dl_nr_arfcn'])
          self.assertEqual(p['n_id_cell'],    conf_ncell['pci'])
          self.assertEqual(p['gnb_id_bits'],  conf_ncell['gnb_id_bits'])
          self.assertEqual(p['nr_cell_id'],   int(conf_ncell['nr_cell_id'], 16))
          self.assertEqual(p['tac'],          conf_ncell['tac'])
          self.assertEqual(p['band'],         conf_ncell['nr_band'])
        tdd_config = conf['nr_cell_default']['tdd_ul_dl_config']['pattern1']
        self.assertEqual(float(tdd_config['period']), 2.5)
        self.assertEqual(int(tdd_config['dl_slots']), 3)
        self.assertEqual(int(tdd_config['dl_symbols']), 10)
        self.assertEqual(int(tdd_config['ul_slots']), 1)
        self.assertEqual(int(tdd_config['ul_symbols']), 2)

        with open(conf_file, 'r') as f:
            for l in f:
                if l.startswith('#define NR_BANDWIDTH'):
                    self.assertIn(str(gnb_param_dict1['nr_bandwidth']), l)

def test_gnb_conf2(self):

        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'gnb.cfg'))[0]

        with open(conf_file, 'r') as f:
            conf = yaml.load(f)

        for p in conf['nr_cell_default']['plmn_list'][0]['nssai']:
          for n in "sd sst".split():
              self.assertEqual(p[n], gnb_param_dict2['nssai'][str(p['sd'])][n])

def test_mme_conf(self):

    conf_file = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'etc', 'mme.cfg'))[0]

    with open(conf_file, 'r') as f:
        conf = yaml.load(f)
    self.assertEqual(conf['plmn'], param_dict['core_network_plmn'])

def test_sim_card(self):

    conf_file = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'ue_db.cfg'))[0]

    with open(conf_file, 'r') as f:
        conf = yaml.load(f)
    for n in "sim_algo imsi opc sqn impu impi".split():
        self.assertEqual(conf['ue_db'][0][n], param_dict[n])
    self.assertEqual(conf['ue_db'][0]['K'], param_dict['k'])
    self.assertEqual(conf['ue_db'][0]['amf'], int(param_dict['amf'], 16))

    p = self.requestSlaveInstance().getConnectionParameterDict()
    p = p['_'] if '_' in p else p
    self.assertIn('info', p)

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

class TestENBParameters(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(enb_param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb"
    def test_enb_conf(self):
        test_enb_conf(self)

class TestGNBParameters1(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(gnb_param_dict1)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "gnb"
    def test_gnb_conf(self):
        test_gnb_conf1(self)

class TestGNBParameters2(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(gnb_param_dict2)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "gnb"
    def test_gnb_conf(self):
        test_gnb_conf2(self)

class TestCoreNetworkParameters(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "core-network"
    def test_mme_conf(self):
        test_mme_conf(self)

def requestSlaveInstance(cls):
    software_url = cls.getSoftwareURL()
    return cls.slap.request(
        software_release=software_url,
        partition_reference="SIM-CARD",
        partition_parameter_kw={'_': json.dumps(param_dict)},
        shared=True,
        software_type='core-network',
    )

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

class TestUELTEMonitorGadgetUrl(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps({'testing': True})}

    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue-lte"

    def test_monitor_gadget_url(self):
      test_monitor_gadget_url(self)

class TestUENRMonitorGadgetUrl(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps({'testing': True})}

    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue-nr"

    def test_monitor_gadget_url(self):
      test_monitor_gadget_url(self)

class TestSimCard(ORSTestCase):
    @classmethod
    def requestDefaultInstance(cls, state='started'):
        default_instance = super(
            ORSTestCase, cls).requestDefaultInstance(state=state)
        cls.requestSlaveInstance()
        return default_instance
    @classmethod
    def requestSlaveInstance(cls):
        return requestSlaveInstance(cls)
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps({'testing': True})}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "core-network"
    def test_sim_card(self):
        test_sim_card(self)

class TestUELTEParameters(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue-lte"
    def test_ue_lte_conf(self):
        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'ue.cfg'))[0]

        with open(conf_file, 'r') as f:
          conf = yaml.load(f)
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['dl_earfcn'], param_dict['dl_earfcn'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['bandwidth'], param_dict['n_rb_dl'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_dl'], param_dict['n_antenna_dl'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_ul'], param_dict['n_antenna_ul'])
        self.assertEqual(conf['ue_list'][0]['rue_addr'], param_dict['rue_addr'])
        self.assertEqual(conf['ue_list'][0]['imsi'], param_dict['imsi'])
        self.assertEqual(conf['ue_list'][0]['K'], param_dict['k'])
        self.assertEqual(conf['ue_list'][0]['sim_algo'], param_dict['sim_algo'])
        self.assertEqual(conf['ue_list'][0]['opc'], param_dict['opc'])
        self.assertEqual(conf['ue_list'][0]['amf'], int(param_dict['amf'], 16))
        self.assertEqual(conf['ue_list'][0]['sqn'], param_dict['sqn'])
        self.assertEqual(conf['ue_list'][0]['impu'], param_dict['impu'])
        self.assertEqual(conf['ue_list'][0]['impi'], param_dict['impi'])
        self.assertEqual(conf['tx_gain'], param_dict['tx_gain'])
        self.assertEqual(conf['rx_gain'], param_dict['rx_gain'])

class TestUENRParameters(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue-nr"
    def test_ue_nr_conf(self):
        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'ue.cfg'))[0]

        with open(conf_file, 'r') as f:
          conf = yaml.load(f)
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['ssb_nr_arfcn'], param_dict['ssb_nr_arfcn'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['dl_nr_arfcn'], param_dict['dl_nr_arfcn'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['bandwidth'], param_dict['nr_bandwidth'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['band'], param_dict['nr_band'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_dl'], param_dict['n_antenna_dl'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_ul'], param_dict['n_antenna_ul'])
        self.assertEqual(conf['ue_list'][0]['rue_addr'], param_dict['rue_addr'])
        self.assertEqual(conf['ue_list'][0]['imsi'], param_dict['imsi'])
        self.assertEqual(conf['ue_list'][0]['K'], param_dict['k'])
        self.assertEqual(conf['ue_list'][0]['sim_algo'], param_dict['sim_algo'])
        self.assertEqual(conf['ue_list'][0]['opc'], param_dict['opc'])
        self.assertEqual(conf['ue_list'][0]['amf'], int(param_dict['amf'], 16))
        self.assertEqual(conf['ue_list'][0]['sqn'], param_dict['sqn'])
        self.assertEqual(conf['ue_list'][0]['impu'], param_dict['impu'])
        self.assertEqual(conf['ue_list'][0]['impi'], param_dict['impi'])
        self.assertEqual(conf['tx_gain'], param_dict['tx_gain'])
        self.assertEqual(conf['rx_gain'], param_dict['rx_gain'])

