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


# ---- building blocks to construct a cell ----

# TDD/FDD are basic parameters to indicate TDD/FDD mode.
TDD = {'rf_mode': 'tdd'}
FDD = {'rf_mode': 'fdd'}

# LTE/NR return basic parameters for an LTE/NR cell with given downlink frequency.
def LTE(dl_earfcn):
    return {
        'cell_type': 'lte',
        'dl_earfcn': dl_earfcn,
    }
def NR(dl_nr_arfcn, nr_band):
    return {
        'cell_type':    'nr',
        'dl_nr_arfcn':  dl_nr_arfcn,
        'nr_band':      nr_band,
    }

# BW returns basic parameters to indicate specified bandwidth.
def BW(bandwidth):
    return {
        'bandwidth':    bandwidth,
    }

# CENB returns basic parameters to indicate a ENB-kind cell.
def CENB(cell_id, pci, tac):
    return {
        'cell_kind':    'enb',
        'cell_id':      '0x%02x' % cell_id,
        'pci':          pci,
        'tac':          '0x%x' % tac,
    }

# LTE_PEER/NR_PEER indicate an LTE/NR ENB-PEER-kind cell.
def LTE_PEER(e_cell_id, pci, tac):
    return {
        'cell_kind': 'enb_peer',
        'e_cell_id': '0x%05x' % e_cell_id,
        'pci':       pci,
        'tac':       '0x%x' % tac,
    }
def NR_PEER(nr_cell_id, gnb_id_bits, pci, tac):
    return {
        'cell_kind': 'enb_peer',
        'nr_cell_id':       '0x77712',
        'gnb_id_bits':      22,
        'pci':              75,
        'tac':              321,
    }

# CUE indicates a UE-kind cell.
CUE   = {'cell_kind': 'ue'}


# ----


PEER4 = {
    'peer_type':    'lte',
    'x2_addr':      '44.1.1.1',
}

PEER4 = {
    'peer_type':    'nr',
    'xn_addr':      '55.1.1.1',
}

PEERCELL4 = LTE(700)      | LTE_PEER(0x12345, 35, 0x123)
PEERCELL5 = NR(520000,38) | NR_PEER(0x77712,28, 75, 0x321)

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


# XXX explain CELL_xy ...   XXX goes away
CELL_4t = TDD | LTE(38050)    | BW( 5)  # 2600 MHz
CELL_5t = TDD | NR(523020,41) | BW(10)  # 2615.1 MHz
CELL_4f = FDD | LTE(3350)     | BW( 5)  # 2680 MHz
CELL_5f = FDD |  NR(537200,7) | BW( 5)  # 2686 MHz


# XXX doc
class ENBTestCase(AmariTestCase):
    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb"

    @classmethod
    def getInstanceParameterDict(cls):
        return json.dumps({...} )    # XXX + testing=True enb_id, gnb_id

    # XXX + generic test that verifies ^^^ to be rendered into enb.cfg

    @classmethod
    def requestDefaultInstance(cls, state='started'):
        inst = super().requestDefaultInstance(state=state)
        cls.requestAllShared(inst)
        return inst

    # ref returns full reference of shared instance with given subreference.
    #
    # for example if reference of main instance is 'MAIN-INSTANCE'
    #
    #   ref('RU') = 'MAIN-INSTANCE.RU'
    @classmethod
    def ref(cls, subref):
        return '%s.%s' % (cls.default_partition_reference, subref)

    # requestAllShared adds all shared instances of the testcase over imain.
    @classmethod
    def requestAllShared(cls, imain):
        def _(subref, ctx):
            return cls.requestShared(imain, subref, ctx)
        _('PEER4',      PEER4)
        _('PEER5',      PEER4)
        _('PEERCELL4',  PEERCELL4)
        _('PEERCELL5',  PEERCELL5)


    # requestShared requests one shared instance over imain with specified subreference and parameters.
    @classmethod
    def requestShared(cls, imain, subref, ctx):
        cls.slap.request(
            software_release=cls.getSoftwareURL(),
            software_type=cls.getInstanceSoftwareType(),
            partition_reference=cls.ref(subref),
            filter_kw = {'instance_guid': imain.getInstanceGuid()},
            partition_parameter_kw={'_': json.dumps(ctx)},
            shared=True)



class TestENB_SDR(ENBTestCase):
    @classmethod
    def requestAllShared(cls, imain):
        super().requestAllShared(cls, imain)

        # sdr0  x 4t
        # sdr1  x 4f
        # sdr2  x 5t
        # sdr3  x 5f


class TestENB_CPRI(ENBTestCase):
    #   lo  x {4t,4f,5t,5f}
    #   sw  x {4t,4f,5t,5f}

    @classmethod
    def requestAllShared(cls, imain):
        super().requestAllShared(imain)

        # Lopcomm x {4t,4f,5t,5f}
        def LO(i):
            return {
                'ru_type':      'lopcomm',
                'ru_link_type': 'cpri',
                'cpri_link':    {
                    'sdr_dev':  0,
                    'sfp_port': 1 + i,
                    'mult':     4,
                    'mapping':  'hw',
                    'rx_delay': 25,
                    'tx_delay': 14,
                    'tx_dbm':   63
                },
                'mac_addr':     '00:0A:45:00:00:%02x' % i,
                'tx_gain':      -11,
                'rx_gain':      -12,
                'txrx_active':  'INACTIVE',
            }
        cls.requestShared(imain, 'LO1', LO(1))
        cls.requestShared(imain, 'LO2', LO(2))
        cls.requestShared(imain, 'LO3', LO(3))
        cls.requestShared(imain, 'LO4', LO(4))

        def LO_CELL(i, **kw):
            cell = {
                'cell_kind':    'enb',
                'pci':          i,
                'cell_id':      '%x' % (0x00 + i),
                'ru': {
                    'ru_type': 'ru_ref',
                    'ru_ref':   cls.ref('LO%d' % i),
                }
            }
            cell.update(kw)
            cls.requestShared(imain, 'LO%d.CELL' % i, cell)

        LO_CELL(1, TDD | LTE(100) | BW(10))
        LO_CELL(2, FDD | LTE(500) | BW(20))
        LO_CELL(3, TDD | NR (100) | BW(10))
        LO_CELL(4, FDD | NR (500) | BW(10))

        # XXX + sunwave

    def test_enb_conf(self):
        super().test_enb_conf()

        conf = yload('%s/etc/enb.cfg' % self.computer_partition_root_path)

        rf_driver = conf['rf_driver']
        self.assertEqual(rf_driver['args'],
                'dev0=/dev/sdr0@1,dev1=/dev/sdr0@2,dev2=/dev/sdr0@3,dev3=/dev/sdr0@4' + # Lopcomm
                '')                                                                     # XXX Sunwave
        self.assertEqual(rf_driver['cpri_mapping'], ','.join(['hw']*4 + ['bf1']*4))
        self.assertEqual(rf_driver['cpri_mult'],    ','.join([ '4']*4 +   ['8']*4))
        self.assertEqual(rf_driver['rx_delay'],     ','.join(['25']*4 +  ['XX']*4))
        self.assertEqual(rf_driver['tx_delay'],     ','.join(['14']*4 +  ['XX']*4))
        self.assertEqual(rf_driver['tx_dbm'],       ','.join(['63']*4 +  ['XX']*4))
        self.assertEqual(rf_driver['ifname'],       ','.join(['XXXX']*4 +  ['YYYY']*4))

        # XXX tx_gain / rx_gain

        self.assertEqual(len(conf['cell_list']),    2*2)
        self.assertEqual(len(conf['nr_cell_list']), 2*2)



        # XXX RU
        # XXX CELLs
        # XXX CA





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
