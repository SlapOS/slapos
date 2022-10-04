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

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, ORSTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software-tdd1900.cfg')))

class TestGNBParameters(ORSTestCase):

    param_dict = {
        'testing': True,
        'nssai': {
            '1': {'sd': '1', 'sst': '10'},
            '2': {'sd': '2', 'sst': '20'},
        },
    }

    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(cls.param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "gnb"
    def test_gnb_conf(self):

        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'gnb.cfg'))[0]

        with open(conf_file, 'r') as f:
            conf = yaml.load(f)

        for p in conf['nr_cell_default']['plmn_list'][0]['nssai']:
          for n in "sd sst".split():
              self.assertEqual(p[n], self.param_dict['nssai'][p['sd']][n])

class TestGNBParameters(ORSTestCase):

    param_dict = {
        'testing': True,
        'tx_gain': 17,
        'rx_gain': 17,
        'dl_nr_arfcn': 325320,
        'nr_band': 99,
        'nr_bandwidth': 50,
        'gnb_id': "0x17",
        'ssb_pos_bitmap': "10",
        'pci': 250,
        'plmn_list': {
            '00101': {'plmn': '00101', 'ranac': 1, 'reserved': True, 'tac': 1},
            '00102': {'plmn': '00102', 'ranac': 2, 'reserved': False, 'tac': 2},
        },
        'amf_list': {
            '10.0.0.1': {'amf_addr': '10.0.0.1'},
            '2001:db8::1': {'amf_addr': '2001:db8::1'},
        },
    }

    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(cls.param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "gnb"
    def test_gnb_conf(self):

        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'gnb.cfg'))[0]

        with open(conf_file, 'r') as f:
            conf = yaml.load(f)
        self.assertEqual(conf['tx_gain'], self.param_dict['tx_gain'])
        self.assertEqual(conf['rx_gain'], self.param_dict['rx_gain'])
        self.assertEqual(conf['nr_cell_list'][0]['dl_nr_arfcn'], self.param_dict['dl_nr_arfcn'])
        self.assertEqual(conf['nr_cell_list'][0]['band'], self.param_dict['nr_band'])
        self.assertEqual(conf['nr_cell_list'][0]['ssb_pos_bitmap'], self.param_dict['ssb_pos_bitmap'])
        self.assertEqual(conf['nr_cell_default']['n_id_cell'], self.param_dict['pci'])
        self.assertEqual(conf['gnb_id'], int(self.param_dict['gnb_id'], 16))
        for p in conf['nr_cell_default']['plmn_list']:
          for n in "plmn ranac reserved tac".split():
              self.assertEqual(p[n], self.param_dict['plmn_list'][p['plmn']][n])
        for p in conf['amf_list']:
          self.assertEqual(p['amf_addr'], self.param_dict['amf_list'][p['amf_addr']]['amf_addr'])

        with open(conf_file, 'r') as f:
            for l in f:
                if l.startswith('#define NR_BANDWIDTH'):
                    self.assertIn(str(self.param_dict['nr_bandwidth']), l)


enb_param_dict = {
    'testing': True,
    'tx_gain': 17,
    'rx_gain': 17,
    'dl_earfcn': 325320,
    'n_rb_dl': 50,
    'enb_id': "0x17",
    'pci': 250,
    'plmn_list': {
        '00101': {'attach_without_pdn': True, 'plmn': '00101', 'reserved': True},
        '00102': {'attach_without_pdn': False, 'plmn': '00102', 'reserved': False},
    },
    'mme_list': {
        '10.0.0.1': {'mme_addr': '10.0.0.1'},
        '2001:db8::1': {'mme_addr': '2001:db8::1'},
    },
}
epc_param_dict = {
    'testing': True,
    'epc_plmn': '00102',
}

ue_param_dict = {
    'testing': True,
    'tx_gain': 17,
    'rx_gain': 17,
    'dl_earfcn': 325320,
    'n_rb_dl': 50,
    'dl_nr_arfcn': 325320,
    'nr_band': 99,
    'nr_bandwidth': 50,
    'ssb_nr_arfcn': 377790,
    'imsi': "001010123456789",
    'k': "00112233445566778899aabbccddeeff",
    'rue_addr': "192.168.99.88",
    'n_antenna_dl': 2,
    'n_antenna_ul': 2,
}

def test_enb_conf(self):

    conf_file = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'etc', 'enb.cfg'))[0]

    with open(conf_file, 'r') as f:
        conf = yaml.load(f)
    self.assertEqual(conf['tx_gain'], enb_param_dict['tx_gain'])
    self.assertEqual(conf['rx_gain'], enb_param_dict['rx_gain'])
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
def test_mme_conf(self):

    conf_file = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'etc', 'mme.cfg'))[0]

    with open(conf_file, 'r') as f:
        conf = yaml.load(f)
    self.assertEqual(conf['plmn'], epc_param_dict['epc_plmn'])

class TestENBParameters(ORSTestCase):

    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(enb_param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb"
    def test_enb_conf(self):
        test_enb_conf(self)

class TestEPCParameters(ORSTestCase):

    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(epc_param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "epc"
    def test_mme_conf(self):
        test_mme_conf(self)

class TestENBEPCParameters(ORSTestCase):

    @classmethod
    def getInstanceParameterDict(cls):
        return {
            '_': json.dumps(dict(enb_param_dict, **epc_param_dict)),
        }
    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb-epc"
    def test_enb_conf(self):
        test_enb_conf(self)
    def test_mme_conf(self):
        test_mme_conf(self)

sim_card_param_dict = {
    "sim_algo": "milenage",
    "imsi": "001010000000331",
    "opc": "000102030405060708090A0B0C0D0E0F",
    "amf": "0x9001",
    "sqn": "000000000000",
    "k": "00112233445566778899AABBCCDDEEFF",
    "impu": "impu331",
    "impi": "impi331@amarisoft.com",
}

def test_ue_db(self):

    conf_file = glob.glob(os.path.join(
      self.slap.instance_directory, '*', 'ue_db.cfg'))[0]

    with open(conf_file, 'r') as f:
        conf = yaml.load(f)
    for n in "sim_algo imsi opc sqn impu impi".split():
        self.assertEqual(conf['ue_db'][0][n], sim_card_param_dict[n])
    self.assertEqual(conf['ue_db'][0]['K'], sim_card_param_dict['k'])
    self.assertEqual(conf['ue_db'][0]['amf'], int(sim_card_param_dict['amf'], 16))

def requestSlaveInstance(cls, software_type):
    software_url = cls.getSoftwareURL()
    return cls.slap.request(
        software_release=software_url,
        partition_reference="SIM-CARD-EPC",
        partition_parameter_kw={'_': json.dumps(sim_card_param_dict)},
        shared=True,
        software_type=software_type,
    )

class TestEPCSimCard(ORSTestCase):
    @classmethod
    def requestDefaultInstance(cls, state='started'):
        default_instance = super(
            ORSTestCase, cls).requestDefaultInstance(state=state)
        cls.requestSlaveInstance()
        return default_instance
    @classmethod
    def requestSlaveInstance(cls):
        requestSlaveInstance(cls, 'epc')
    @classmethod
    def getInstanceParameterDict(cls):
        return {
            '_': json.dumps({'testing': True})
        }
    @classmethod
    def getInstanceSoftwareType(cls):
        return "epc"

    def test_sim_card(self):
        self.slap.waitForInstance() # Wait until publish is done
        test_ue_db(self)

class TestENBEPCSimCard(ORSTestCase):
    @classmethod
    def requestDefaultInstance(cls, state='started'):
        default_instance = super(
            ORSTestCase, cls).requestDefaultInstance(state=state)
        cls.requestSlaveInstance()
        return default_instance
    @classmethod
    def requestSlaveInstance(cls):
        requestSlaveInstance(cls, 'enb-epc')
    @classmethod
    def getInstanceParameterDict(cls):
        return {
            '_': json.dumps({'testing': True})
        }
    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb-epc"

    def test_sim_card(self):
        self.slap.waitForInstance() # Wait until publish is done
        test_ue_db(self)

class TestGNBEPCSimCard(ORSTestCase):
    @classmethod
    def requestDefaultInstance(cls, state='started'):
        default_instance = super(
            ORSTestCase, cls).requestDefaultInstance(state=state)
        cls.requestSlaveInstance()
        return default_instance
    @classmethod
    def requestSlaveInstance(cls):
        requestSlaveInstance(cls, 'gnb-epc')
    @classmethod
    def getInstanceParameterDict(cls):
        return {
            '_': json.dumps({'testing': True})
        }
    @classmethod
    def getInstanceSoftwareType(cls):
        return "gnb-epc"

    def test_sim_card(self):
        self.slap.waitForInstance() # Wait until publish is done
        test_ue_db(self)

class TestUELTEParameters(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(ue_param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue-lte"
    def test_ue_lte_conf(self):
        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'ue.cfg'))[0]

        with open(conf_file, 'r') as f:
          conf = yaml.load(f)
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['dl_earfcn'], ue_param_dict['dl_earfcn'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['bandwidth'], ue_param_dict['n_rb_dl'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_dl'], ue_param_dict['n_antenna_dl'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_ul'], ue_param_dict['n_antenna_ul'])
        self.assertEqual(conf['ue_list'][0]['rue_addr'],ue_param_dict['rue_addr'])     
        self.assertEqual(conf['ue_list'][0]['imsi'], ue_param_dict['imsi'])
        self.assertEqual(conf['ue_list'][0]['K'], ue_param_dict['k'])
        self.assertEqual(conf['tx_gain'], ue_param_dict['tx_gain'])
        self.assertEqual(conf['rx_gain'], ue_param_dict['rx_gain'])

class TestUENRParameters(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps(ue_param_dict)}
    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue-nr"
    def test_ue_nr_conf(self):
        conf_file = glob.glob(os.path.join(
          self.slap.instance_directory, '*', 'etc', 'ue.cfg'))[0]

        with open(conf_file, 'r') as f:
          conf = yaml.load(f)
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['ssb_nr_arfcn'], ue_param_dict['ssb_nr_arfcn'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['dl_nr_arfcn'], ue_param_dict['dl_nr_arfcn'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['bandwidth'], ue_param_dict['nr_bandwidth'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['band'], ue_param_dict['nr_band'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_dl'], ue_param_dict['n_antenna_dl'])
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['n_antenna_ul'], ue_param_dict['n_antenna_ul'])
        self.assertEqual(conf['ue_list'][0]['rue_addr'],ue_param_dict['rue_addr'])     
        self.assertEqual(conf['ue_list'][0]['imsi'], ue_param_dict['imsi'])
        self.assertEqual(conf['ue_list'][0]['K'], ue_param_dict['k'])
        self.assertEqual(conf['tx_gain'], ue_param_dict['tx_gain'])
        self.assertEqual(conf['rx_gain'],ue_param_dict['rx_gain'])

