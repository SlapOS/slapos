# Copyright (C) 2023  Nexedi SA and Contributors.
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.

import os

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, ORSTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

# XXX

# XXX enb   - {sdr,lopcomm,sunwave}·2 - {cell_lte1fdd,2tdd, cell_nr1fdd,2tdd}  + peer·2 + peercell·2
# XXX uesim - {sdr,lopcomm,sunwave}·2

# XXX core-network - skip - verified by ors

"""
class TestUELTEParameters(ORSTestCase):     # XXX adjust
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

        1/0 # XXX self.assertEqual(cell['n_rb_dl'], 50)
        with open(conf_file, 'r') as f:
            for l in f:
                if l.startswith('#define N_RB_DL'):
                    self.assertIn('50', l)

class TestUENRParameters(ORSTestCase):      # XXX adjust
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
        self.assertEqual(conf['cell_groups'][0]['cells'][0]['bandwidth'], '10 MHz')
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
"""
