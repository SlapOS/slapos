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
import io
import yaml
import pcpp

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, AmariTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


# yload loads yaml config file after preprocessing it.
#
# preprocessing is needed to e.g. remove // and /* comments.
def yload(path):
    with open(path, 'r') as f:
        data = f.read()     # original input
    p = pcpp.Preprocessor()
    p.parse(data)
    f = io.StringIO()
    p.write(f)
    data_ = f.getvalue()    # preprocessed input
    return yaml.load(data_, Loader=yaml.Loader)



# XXX explain CELL_xy ...
CELL_4t = {
    'cell_type':    'lte',
    'rf_mode':      'tdd',
    'bandwidth':    '5 MHz',
    'dl_earfcn':    38050,      # 2600 MHz
}

CELL_5t = {
    'cell_type':    'nr',
    'rf_mode':      'tdd',
    'bandwidth':    10,
    'dl_nr_arfcn':  523020,     # 2615.1 MHz
    'nr_band':      41,
}

CELL_4f = {
    'cell_type':    'lte',
    'rf_mode':      'fdd',
    'bandwidth':    '5 MHz',
    'dl_earfcn':    3350,       # 2680 MHz
}

CELL_5f = {
    'cell_type':    'nr',
    'rf_mode':      'fdd',
    'bandwidth':    5,
    'dl_nr_arfcn':  537200,     # 2686 MHz
    'nr_band':      7,
}


# XXX common enb
_ = {
    'cell_kind':    'enb',
    'pci':          1,          # XXX
    'cell_id':      '0x01',     # XXX
    'tac':          '0x1234',
}

# XXX common uesim
_ = {
    'cell_kind':    'ue',
}


PEER4 = {
    'peer_type':    'lte',
    'x2_addr':      '44.1.1.1',
}

PEER4 = {
    'peer_type':    'nr',
    'xn_addr':      '55.1.1.1',
}

PEERCELL4 = {
    'cell_type':        'lte',
    'cell_kind':        'enb_peer',
    'e_cell_id':        '0x12345',
    'pci':              35,
    'dl_earfcn':        700,
    'bandwidth':        '10 MHz',
    'tac':              123,
}


PEERCELL5 = {
    'cell_type':        'nr',
    'cell_kind':        'enb_peer',
    'nr_cell_id':       '0x77712',
    'gnb_id_bits':      22,
    'dl_nr_arfcn':      520000,
    'nr_band':          38,
    'pci':              75,
    'tac':              321,
}

# XXX dl_earfcn     -> ul_earfcn
# XXX dl_nr_arfcn   -> ul_nr_arfcn + ssb_nr_arfcn

# XXX explain ENB does not support mixing SDR + CPRI

# XXX doc
class ENBTestCase(AmariTestCase):
    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb"

    # ref returns full reference of shared instance with given subreference.
    #
    # for example if refrence of main isntance is 'MAIN-INSTANCE'
    #
    #   ref('RU') = 'MAIN-INSTANCE.RU'
    @classmethod
    def ref(cls, subref):
        return '%s.%s' % (cls.default_partition_reference, subref)

    @classmethod
    def requestDefaultInstance(cls, state='started'):
        inst = super().requestDefaultInstance(state=state)
        cls.addShared(inst)
        return inst

    # addShared adds all shared instances of the testcase over imain.
    @classmethod
    def addShared(cls, imain):
        def _(subref, ctx):
            return cls.requestShared(imain, subref, ctx)
        _('PEER4',      PEER4)
        _('PEER5',      PEER4)
        _('PEERCELL4',  PEERCELL4)
        _('PEERCELL5',  PEERCELL5)


    # requestShared requests shared instance over imain with specified subreference and parameters.
    @classmethod
    def requestShared(cls, imain, subref, ctx):
        cls.slap.request(
            software_release=cls.getSoftwareURL(),
            software_type=cls.getInstanceSoftwareType(),
            partition_reference=cls.ref(subref),
            filter_kw = {'instance_guid': imain.getInstanceGuid()},
            partition_parameter_kw={'_': json.dumps(ctx)}
            shared=True)



class TestENB_SDR(ENBTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        sdr0  x 4t
        sdr1  x 4f
        sdr2  x 5t
        sdr3  x 5f
        return {'_': json.dumps(enb_param_dict)}


class TestENB_CPRI(ENBTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        lo  x {4t,4f,5t,5f}
        sw  x {4t,4f,5t,5f}


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

class TestUEMonitorGadgetUrl(ORSTestCase):
    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps({'testing': True})}

    @classmethod
    def getInstanceSoftwareType(cls):
        return "ue"

    def test_monitor_gadget_url(self):
      test_monitor_gadget_url(self)
"""
