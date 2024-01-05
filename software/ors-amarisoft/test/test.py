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
import json
import io
import yaml
import pcpp

import unittest
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, AmariTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


# ---- building blocks to construct cell/peer parameters ----
#
# - TDD/FDD indicate TDD/FDD mode.
# - LTE/NR  indicate LTE/NR cell with given downlink frequency.
# - BW      indicates specified bandwidth.
# - CENB    indicates a ENB-kind cell.
# - CUE     indicates an UE-kind cell.
# - TAC     indicates specified Traking Area Code.
# - LTE_PEER/NR_PEER indicate an LTE/NR ENB-PEER-kind cell.
# - X2_PEER/XN_PEER  indicate an LTE/NR ENB peer.

# TDD/FDD are basic parameters to indicate TDD/FDD mode.
TDD = {'rf_mode': 'tdd'}
FDD = {'rf_mode': 'fdd'}

# LTE/NR return basic parameters for an LTE/NR cell with given downlink frequency.
def LTE(dl_earfcn):
    return {
        'cell_type':    'lte',
        'dl_earfcn':    dl_earfcn,
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
def CENB(cell_id, pci):
    return {
        'cell_kind':    'enb',
        'cell_id':      '0x%02x' % cell_id,
        'pci':          pci,
    }

# CUE indicates an UE-kind cell.
def CUE(): ...  # XXX

#  TAC returns basic parameters to indicate specified Traking Area Code.
def TAC(tac):
    return {
        'tac':          '0x%x' % tac,
    }

CUE = {'cell_kind': 'ue'}

# LTE_PEER/NR_PEER return basic parameters to indicate an LTE/NR ENB-PEER-kind cell.
def LTE_PEER(e_cell_id, pci, tac):
    return {
        'cell_kind':    'enb_peer',
        'e_cell_id':    '0x%07x' % e_cell_id,
        'pci':          pci,
        'tac':          '0x%x' % tac,
    }
def NR_PEER(nr_cell_id, gnb_id_bits, pci, tac):
    return {
        'cell_kind':    'enb_peer',
        'nr_cell_id':   '0x%09x' % nr_cell_id,
        'gnb_id_bits':  gnb_id_bits,
        'pci':          pci,
        'tac':          tac,
    }

# X2_PEER/XN_PEER return basic parameters to indicate an LTE/NR ENB peer.
def X2_PEER(x2_addr):
    return {
        'peer_type':    'lte',
        'x2_addr':      x2_addr,
    }
def XN_PEER(xn_addr):
    return {
        'peer_type':    'nr',
        'xn_addr':      xn_addr,
    }

# ----


# XXX doc
# XXX approach is to test generated enb.cfg
class ENBTestCase(AmariTestCase):
    maxDiff = None  # want to see full diff in test run log on an error

    @classmethod
    def getInstanceSoftwareType(cls):
        return "enb"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.enb_cfg = yamlpp_load(cls.ipath('etc/enb.cfg'))

    @classmethod
    def getInstanceParameterDict(cls):
        return {'_': json.dumps({
            'testing':      True,
            'enb_id':       '0x17',
            'gnb_id':       '0x23',
            'gnb_id_bits':  30,
        })}

    @classmethod
    def requestDefaultInstance(cls, state='started'):
        inst = super().requestDefaultInstance(state=state)
        cls.requestAllShared(inst)
        return inst

    # requestAllShared adds all shared instances of the testcase over imain.
    @classmethod
    def requestAllShared(cls, imain):
        def _(subref, ctx):
            return cls.requestShared(imain, subref, ctx)
        _('PEER4',      X2_PEER('44.1.1.1'))
        _('PEER5',      XN_PEER('55.1.1.1'))

        _('PEERCELL4',  LTE(700)      | LTE_PEER(0x12345,    35, 0x123))
        _('PEERCELL5',  NR(520000,38) |  NR_PEER(0x77712,22, 75, 0x321))
        cls.ho_inter = [
            dict(rat='eutra', cell_id=0x12345, n_id_cell=35, dl_earfcn=  700, tac=0x123),
            dict(rat='nr',    nr_cell_id=0x77712, gnb_id_bits=22, n_id_cell=75,
                 dl_nr_arfcn=520000, ul_nr_arfcn=520000, ssb_nr_arfcn=520090, band=38,
                 tac = 0x321),
        ]

        # XXX doc 4 RU x 4 CELL  (4f,4t,5f,5t)      RUcfg
        def RU(i):
            ru = cls.RUcfg(i)
            ru = ru | {'tx_gain': 10+i, 'rx_gain':  20+i, 'txrx_active': 'INACTIVE'}
            cls.requestShared(imain, 'RU%d' % i, ru)

        def CELL(i, ctx):
            cell = {
                'ru': {
                    'ru_type': 'ru_ref',
                    'ru_ref':   cls.ref('RU%d' % i),
                }
            }
            cell.update(CENB(i, 0x10+i))
            cell.update({'root_sequence_index': 200+i,
                         'inactivity_timer':    1000+i})
            cell.update(ctx)
            cls.requestShared(imain, 'RU%d.CELL' % i, cell)

        RU(1);  CELL(1, FDD | LTE(   100)    | BW( 5) | TAC(0x101))
        RU(2);  CELL(2, TDD | LTE( 36100)    | BW(10) | TAC(0x102))
        RU(3);  CELL(3, FDD | NR (430100, 1) | BW(15))
        RU(4);  CELL(4, TDD | NR (510100,41) | BW(20))

    # requestShared requests one shared instance over imain with specified subreference and parameters.
    @classmethod
    def requestShared(cls, imain, subref, ctx):
        cls.slap.request(
            software_release=cls.getSoftwareURL(),
            software_type=cls.getInstanceSoftwareType(),
            partition_reference=cls.ref(subref),
            # XXX StandaloneSlapOS rejects filter_kw with "Can only request on embedded computer"
            #filter_kw = {'instance_guid': imain.getInstanceGuid()},
            partition_parameter_kw={'_': json.dumps(ctx)},
            shared=True)

    # ref returns full reference of shared instance with given subreference.
    #
    # for example if reference of main instance is 'MAIN-INSTANCE'
    #
    #   ref('RU') = 'MAIN-INSTANCE.RU'
    @classmethod
    def ref(cls, subref):
        return '%s.%s' % (cls.default_partition_reference, subref)

    # ipath returns path for a file inside main instance.
    @classmethod
    def ipath(cls, path):
        assert path[:1] != '/', path
        return '%s/%s' % (cls.computer_partition_root_path, path)

    # --------

    def test_enb_conf_basic(t):
        assertMatch(t, t.enb_cfg, dict(
            enb_id=0x17, gnb_id=0x23, gnb_id_bits=30,
            x2_peers=['44.1.1.1'], xn_peers=['55.1.1.1'],
        ))

        # XXX kill
        """
        # HO(inter)
        for cell in t.enb_cfg['cell_list'] + t.enb_cfg['nr_cell_list']:
            have = {
                'cell_id':          cell['cell_id'],
                'ncell_list_tail':  cell['ncell_list'] [-len(t.ho_inter):]
            }
            want = {
                'cell_id':          cell['cell_id'],
                'ncell_list_tail':  t.ho_inter
            }
            assertMatch(t, have, want)
        """

    # basic cell parameters
    def test_enb_conf_cell(t):
        assertMatch(t, t.enb_cfg['cell_list'],  [
          dict( # CELL1
            uldl_config=NO,   rf_port=0,        n_antenna_dl=4,  n_antenna_ul=2,
            dl_earfcn=100,    ul_earfcn=18100,
            n_rb_dl=25,
            cell_id=0x1,      n_id_cell=0x11,   tac=0x101,
            root_sequence_index=201,  inactivity_timer=1001,
          ),
          dict( # CELL2
            uldl_config=2,    rf_port=1,        n_antenna_dl=4,  n_antenna_ul=2,
            dl_earfcn=36100,  ul_earfcn=36100,
            n_rb_dl=50,
            cell_id=0x2,      n_id_cell=0x12,   tac=0x102,
            root_sequence_index=202,  inactivity_timer=1002,
          ),
        ])

        assertMatch(t, t.enb_cfg['nr_cell_list'],  [
          dict( # CELL3
            tdd_ul_dl_config=NO, rf_port=2,           n_antenna_dl=4,       n_antenna_ul=2,
            dl_nr_arfcn=430100,  ul_nr_arfcn=392100,  ssb_nr_arfcn=429890,  band=1,
            bandwidth=15,
            cell_id=0x3,         n_id_cell=0x13,      tac=NO,
            root_sequence_index=203,  inactivity_timer=1003,
          ),

          dict( # CELL4
            tdd_ul_dl_config={'pattern1': dict(
                period=5, dl_slots=7, dl_symbols=6, ul_slots=2, ul_symbols=4,
            )},
                                 rf_port=3,           n_antenna_dl=4,       n_antenna_ul=2,
            dl_nr_arfcn=510100,  ul_nr_arfcn=510100,  ssb_nr_arfcn=510010,  band=41,
            bandwidth=20,
            cell_id=0x4,         n_id_cell=0x14,      tac=NO,
            root_sequence_index=204,  inactivity_timer=1004,
          ),
        ])


    # Carrier Aggregation
    def test_enb_conf_ca(t):
        assertMatch(t, t.enb_cfg['cell_list'],  [
          { # CELL1
            'scell_list':           [{'cell_id': 0x2}],                     # LTE + LTE
            'en_dc_scg_cell_list':  [{'cell_id': 0x3}, {'cell_id': 0x4}],   # LTE + NR
          },
          { # CELL2
            'scell_list':           [{'cell_id': 0x1}],                     # LTE + LTE
            'en_dc_scg_cell_list':  [{'cell_id': 0x3}, {'cell_id': 0x4}],   # LTE + NR
          },
        ])

        assertMatch(t, t.enb_cfg['nr_cell_list'], [
          { # CELL3
            'scell_list':           [{'cell_id': 0x4}],                     # NR  + NR
          },
          { # CELL4
            'scell_list':           [{'cell_id': 0x3}],                     # NR  + NR
          },
        ])


    # Handover
    def test_enb_conf_ho(t):
        assertMatch(t, t.enb_cfg['cell_list'],  [
          { # CELL1
            'ncell_list':   [
              dict(rat='eutra', cell_id= 0x1702, n_id_cell=0x12, dl_earfcn=36100, tac=0x102), # CELL2
              dict(rat='nr',    cell_id=   0x03),                                             # CELL3
              dict(rat='nr',    cell_id=   0x04),                                             # CELL4
            ] + t.ho_inter,
          },
          { # CELL2
            'ncell_list':   [
              dict(rat='eutra', cell_id= 0x1701, n_id_cell=0x11, dl_earfcn=  100, tac=0x101), # CELL1
              dict(rat='nr',    cell_id=   0x03),                                             # CELL3
              dict(rat='nr',    cell_id=   0x04),                                             # CELL4
            ] + t.ho_inter,
          },
        ])
        assertMatch(t, t.enb_cfg['nr_cell_list'], [
          { # CELL3
            'ncell_list':   [
              dict(rat='eutra', cell_id= 0x1701, n_id_cell=0x11, dl_earfcn=  100, tac=0x101), # CELL1
              dict(rat='eutra', cell_id= 0x1702, n_id_cell=0x12, dl_earfcn=36100, tac=0x102), # CELL2
              dict(rat='nr',    cell_id=   0x04),                                             # CELL4
            ] + t.ho_inter,
          },
          { # CELL4
            'ncell_list':   [
              dict(rat='eutra', cell_id= 0x1701, n_id_cell=0x11, dl_earfcn=  100, tac=0x101), # CELL1
              dict(rat='eutra', cell_id= 0x1702, n_id_cell=0x12, dl_earfcn=36100, tac=0x102), # CELL2
              dict(rat='nr',    cell_id=   0x03),                                             # CELL3
            ] + t.ho_inter,
          },
        ])


# XXX SDR driver in all modes
class TestENB_SDR(ENBTestCase):
    @classmethod
    def RUcfg(cls, i):
        return {
            'ru_type':      'sdr',
            'ru_link_type': 'sdr',
            'sdr_dev_list': [2*i,2*i+1],
            'n_antenna_dl': 4,
            'n_antenna_ul': 2,
        }

    # radio units configuration
    def test_enb_conf_ru(t):
        rf_driver = t.enb_cfg['rf_driver']
        t.assertEqual(rf_driver['args'],
                'dev0=/dev/sdr2,dev1=/dev/sdr3,dev2=/dev/sdr4,dev3=/dev/sdr5,' +
                'dev4=/dev/sdr6,dev5=/dev/sdr7,dev6=/dev/sdr8,dev7=/dev/sdr9')

        # XXX -> generic ?      XXX no (for cpri case it is all 0 here)
        t.assertEqual(t.enb_cfg['tx_gain'], [11]*4 + [12]*4 + [13]*4 + [14]*4)
        t.assertEqual(t.enb_cfg['rx_gain'], [21]*2 + [22]*2 + [23]*2 + [24]*2)


# XXX Lopcomm driver in all modes
class TestENB_Lopcomm(ENBTestCase):
    @classmethod
    def RUcfg(cls, i):
        return {
            'ru_type':      'lopcomm',
            'ru_link_type': 'cpri',
            'cpri_link':    {
                'sdr_dev':  0,
                'sfp_port': i,
                'mult':     4,
                'mapping':  'hw',
                'rx_delay': 40+i,
                'tx_delay': 50+i,
                'tx_dbm':   60+i
            },
            'mac_addr':     '00:0A:45:00:00:%02x' % i,
        }



# XXX not possible to test Lopcomm nor Sunwave because on "slapos standalone" there is no slaptap.
# XXX -> possible  - adjust SR with testing=True workaround
# XXX explain ENB does not support mixing SDR + CPRI
class _TestENB_CPRI(ENBTestCase):
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
        #cls.requestShared(imain, 'LO2', LO(2))
        #cls.requestShared(imain, 'LO3', LO(3))
        #cls.requestShared(imain, 'LO4', LO(4))

        def LO_CELL(i, ctx):
            cell = {
                'ru': {
                    'ru_type': 'ru_ref',
                    'ru_ref':   cls.ref('LO%d' % i),
                }
            }
            cell.update(CENB(i, i))
            cell.update(ctx)
            cls.requestShared(imain, 'LO%d.CELL' % i, cell)

        LO_CELL(1, FDD | LTE(   100)    | BW(10))
        #LO_CELL(2, TDD | LTE( 36100)    | BW(10))
        #LO_CELL(3, FDD | NR (430100, 1) | BW(10))
        #LO_CELL(4, TDD | NR (510100,41) | BW(10))

        # XXX + sunwave

    def test_enb_conf(self):
        super().test_enb_conf()

        conf = yamlpp_load('%s/etc/enb.cfg' % self.computer_partition_root_path)

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


# ---- misc ----

# yamlpp_load loads yaml config file after preprocessing it.
#
# preprocessing is needed to e.g. remove // and /* comments.
def yamlpp_load(path):
    with open(path, 'r') as f:
        data = f.read()     # original input
    p = pcpp.Preprocessor()
    p.parse(data)
    f = io.StringIO()
    p.write(f)
    data_ = f.getvalue()    # preprocessed input
    return yaml.load(data_, Loader=yaml.Loader)


# assertMatch recursively matches data structure against specified pattern.
#
# - dict match by verifying v[k] == vok[k] for keys from the pattern.
#   vok[k]=NO means v[k] must be absent
# - list match by matching all elements individually
# - atomic types like int and str match by equality
class NOClass:
    def __repr__(self):
        return 'ø'
NO = NOClass()
def assertMatch(t: unittest.TestCase, v, vok):
    v_ = _matchCollect(v, vok)
    t.assertEqual(v_, vok)

def _matchCollect(v, vok):
    if type(v) is not type(vok):
        return v
    if type(v) is dict:
        v_ = {}
        for k in vok:
            #v_[k] = v.get(k, NO)
            v_[k] = _matchCollect(v.get(k, NO), vok[k])
        return v_
    if type(v) is list:
        v_ = []
        for i in range(max(len(v), len(vok))):
            e   = NO
            eok = NO
            if i < len(v):
                e = v[i]
            if i < len(vok):
                eok = vok[i]

            if e is not NO:
                if eok is not NO:
                    v_.append(_matchCollect(e, eok))
                else:
                    v_.append(e)
        return v_

    # other types, e.g. atomic int/str/... - return as is
    assert type(v) is not tuple, v
    return v


# XXX test for assertMatch
