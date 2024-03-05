# Copyright (C) 2022-2024  Nexedi SA and Contributors.
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

# Unit-tests for generic software for Amarisoft 4G/5G stack.
#
# Here we verify only generated configurations because it is not possible to
# run Amarisoft software on testnodes due to licensing restrictions. End-to-end
# testing complements unit-testing by verifying how LTE works for real, but it
# needs dedicated hardware test setup.
#
# Here we test:
#
# - enb     (see TestENB_*)
# - uesim   (see TestUEsim_*)
#
# Currently there is no tests for core-network, because for core-network
# there is no difference in between generic and ORS modes and core-network is
# already verified by test_ors.


import os
import json
import io
import yaml
import pcpp
import xmltodict

import sys
sys.path.insert(0, '../ru')
import xbuildout

import unittest
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, _AmariTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


# ---- building blocks to construct cell/peer parameters ----
#
# - TDD/FDD indicate TDD/FDD mode.
# - LTE/NR  indicate LTE/NR cell with given downlink frequency.
# - BW      indicates specified bandwidth.
# - CENB    indicates a ENB-kind cell.
# - CUE     indicates an UE-kind cell.
# - TAC     indicates specified Tracking Area Code.
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
CUE = {'cell_kind': 'ue'}

#  TAC returns basic parameters to indicate specified Tracking Area Code.
def TAC(tac):
  return {
      'tac':          '0x%x' % tac,
  }

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

# --------

# AmariTestCase is base class for all tests.
class AmariTestCase(_AmariTestCase):
  maxDiff = None  # show full diff in test run log on an error

  # stress correctness of ru_ref/cell_ref/... usage throughout all places in
  # buildout code - special characters should not lead to wrong templates or
  # code injection.
  default_partition_reference = _AmariTestCase.default_partition_reference + \
                                ' ${a:b}\n[c]\n;'

  # faster edit/try cycle when enabled (handy during development)
  if 0:
    instance_max_retry = 1
    report_max_retry = 1

  @classmethod
  def requestDefaultInstance(cls, state='started'):
    inst = super().requestDefaultInstance(state=state)
    cls.requestAllShared(inst)
    return inst

  # requestAllShared should add all shared instances of the testcase over imain.
  @classmethod
  def requestAllShared(cls, imain):
    raise NotImplementedError

  # requestShared requests one shared instance over imain with specified subreference and parameters.
  @classmethod
  def requestShared(cls, imain, subref, ctx):
    ref = cls.ref(subref)
    kw = dict(
        software_release=cls.getSoftwareURL(),
        software_type=cls.getInstanceSoftwareType(),
        partition_reference=ref,
        # XXX StandaloneSlapOS rejects filter_kw with "Can only request on embedded computer"
        #filter_kw = {'instance_guid': imain.getInstanceGuid()},
        partition_parameter_kw={'_': json.dumps(ctx)},
        shared=True)
    cls._requested[ref] = kw
    return cls.slap.request(**kw)

  # XXX StandaloneSlapOS lacks getInformation - we remember the way instances are requested ourselves.
  _requested = {} # ref -> kw used for slap.request

  # queryPublished and querySharedPublished return information published by
  # an instance / shared instance correspondingly.
  @classmethod
  def querySharedPublished(cls, subref):
    return cls.queryPublished(cls.ref(subref))

  @classmethod
  def queryPublished(cls, ref):
    # see ^^^ about lack of getInformation on StandaloneSlapOS
    #inst = cls.slap.getInformation(computer_partition=ref)
    inst = cls.slap.request(**cls._requested[ref])
    iconn = inst.getConnectionParameterDict()
    return json.loads(iconn['_'])


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


# ---- eNB + base class for similar services that do radio ----

# RFTestCase4 is base class for tests of all services that do radio.
#
# It instantiates a service with several Radio Units and Cells attached:
#
# 4 RU x 4 CELL are requested to verify all {FDD,TDD}·{LTE,NR} combinations.
#
# In requested instances mostly non-overlapping range of numbers are
# assigned to parameters according to the following scheme:
#
#   0+          cell_id
#   0x10+       pci
#   0x100+      tac
#   10+         tx_gain
#   20+         rx_gain
#   xxx+i·100   dl_arfcn
#   5,10,15,20  bandwidth
#   100+        root_sequence_index
#   1000+       inactivity_timer
#
# this allows to quickly see offhand to which cell/ru and parameter a
# particular number belongs to.
#
# Subclasses should define:
#
# - RUcfg(i) to return primary parameters specific for i'th RU configuration
#   like ru_type - to verify particular RU driver, sdr_dev, sfp_port and so on.
# - CELLcfg(i) to tune parameters of i'th cell, for example cell_kind.
# - .rf_cfg with loaded service config.
class RFTestCase4(AmariTestCase):
  @classmethod
  def requestAllShared(cls, imain):
    def RU(i):
      ru = cls.RUcfg(i)
      ru |= {'n_antenna_dl': 4, 'n_antenna_ul': 2}
      ru |= {'tx_gain': 10+i, 'rx_gain':  20+i, 'txrx_active': 'ACTIVE'}
      return cls.requestShared(imain, 'RU%d' % i, ru)

    def CELL(i, ctx):
      cell = {
          'ru': {
              'ru_type': 'ru_ref',
              'ru_ref':   cls.ref('RU%d' % i),
          }
      }
      cell |= cls.CELLcfg(i)
      cell |= ctx
      return cls.requestShared(imain, 'RU%d.CELL' % i, cell)

    RU(1);  CELL(1, FDD | LTE(   100)    | BW( 5))
    RU(2);  CELL(2, TDD | LTE( 40200)    | BW(10))
    RU(3);  CELL(3, FDD | NR (300300,74) | BW(15))
    RU(4);  CELL(4, TDD | NR (470400,40) | BW(20))

  def test_rf_cfg_txrx_gain(t):
    # NOTE even though setting tx_gain/rx_gain in enb.cfg does not make any
    #      difference for CPRI case, we still do set it there for consistency.
    #      For the reference: for CPRI case the real tx/rx gain is set in
    #      RU configuration and is verified by RU tests.
    t.assertEqual(t.rf_cfg['tx_gain'], [11]*4 + [12]*4 + [13]*4 + [14]*4)
    t.assertEqual(t.rf_cfg['rx_gain'], [21]*2 + [22]*2 + [23]*2 + [24]*2)

  def test_published_ru_and_cell(t):
    q = t.querySharedPublished
    assertMatch(t, q('RU1'), {'tx_gain': 11, 'rx_gain': 21, 'txrx_active': 'ACTIVE'})
    assertMatch(t, q('RU2'), {'tx_gain': 12, 'rx_gain': 22, 'txrx_active': 'ACTIVE'})
    assertMatch(t, q('RU3'), {'tx_gain': 13, 'rx_gain': 23, 'txrx_active': 'ACTIVE'})
    assertMatch(t, q('RU4'), {'tx_gain': 14, 'rx_gain': 24, 'txrx_active': 'ACTIVE'})

    assertMatch(t, q('RU1.CELL'), dict(band='b1',
                        dl_earfcn=  100,    ul_earfcn=18100,
                        dl_nr_arfcn=NO,     ul_nr_arfcn=NO,     ssb_nr_arfcn=NO))
    assertMatch(t, q('RU2.CELL'), dict(band='b41',
                        dl_earfcn=40200,    ul_earfcn=40200,
                        dl_nr_arfcn=NO,     ul_nr_arfcn=NO,     ssb_nr_arfcn=NO))
    assertMatch(t, q('RU3.CELL'), dict(band='n74',
                        dl_earfcn=NO,       ul_earfcn=NO,
                        dl_nr_arfcn=300300, ul_nr_arfcn=290700, ssb_nr_arfcn=300270))
    assertMatch(t, q('RU4.CELL'), dict(band='n40',
                        dl_earfcn=NO,       ul_earfcn=NO,
                        dl_nr_arfcn=470400, ul_nr_arfcn=470400, ssb_nr_arfcn=470430))


# ENBTestCase4 provides base class for unit-testing eNB service.
#
# It instantiates enb with 4 Radio Units x 4 Cells and verifies generated
# enb.cfg to match what is expected.
class ENBTestCase4(RFTestCase4):
  @classmethod
  def getInstanceSoftwareType(cls):
    return "enb"

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.enb_cfg = cls.rf_cfg = yamlpp_load(cls.ipath('etc/enb.cfg'))

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
        'testing':      True,
        'enb_id':       '0x17',
        'gnb_id':       '0x23',
        'gnb_id_bits':  30,
        'mme_list':     {
            '1': {'mme_addr': '1.2.3.4'},
            '2': {'mme_addr': '[abcd:5::1]:78'},
        },
        'amf_list':     {
            '1': {'amf_addr': '4.3.2.1:77'},
            '2': {'amf_addr': 'dcba:5::1'},
        },
        'plmn_list':    {
            '1': {'plmn': '31415'},
            '2': {'plmn': '44444', 'attach_without_pdn': True, 'reserved': True},
        },
        'plmn_list_5g':     {
            '1': {'plmn': '51413', 'tac': 0x124},
            '2': {'plmn': '55555', 'tac': 0x125, 'ranac': 210, 'reserved': True},
        },
    })}

  @classmethod
  def requestAllShared(cls, imain):
    super().requestAllShared(imain)

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

  def CELLcfg(i):
    return CENB(i, 0x10+i) | TAC(0x100+i) | {
             'root_sequence_index': 100+i,
             'inactivity_timer':    1000+i}

  # basic enb parameters
  def test_enb_cfg_basic(t):
    assertMatch(t, t.enb_cfg, dict(
      enb_id=0x17, gnb_id=0x23, gnb_id_bits=30,
      mme_list=[{'mme_addr': '1.2.3.4'}, {'mme_addr': '[abcd:5::1]:78'}],
      amf_list=[{'amf_addr': '4.3.2.1:77'}, {'amf_addr': 'dcba:5::1'}],
      x2_peers=['44.1.1.1'], xn_peers=['55.1.1.1'],
      cell_default={
        'plmn_list': [
          dict(plmn='31415', attach_without_pdn=False, reserved=False),
          dict(plmn='44444', attach_without_pdn=True,  reserved=True),
        ]
      },
      nr_cell_default={
        'plmn_list': [
          dict(plmn='51413', tac=0x124, ranac=NO,  reserved=False),
          dict(plmn='55555', tac=0x125, ranac=210, reserved=True),
        ]
      },
    ))

  # basic cell parameters
  def test_enb_cfg_cell(t):
    assertMatch(t, t.enb_cfg['cell_list'],  [
      dict( # CELL1
        uldl_config=NO,   rf_port=0,        n_antenna_dl=4,  n_antenna_ul=2,
        dl_earfcn=100,    ul_earfcn=18100,
        n_rb_dl=25,
        cell_id=0x1,      n_id_cell=0x11,   tac=0x101,
        root_sequence_index=101,  inactivity_timer=1001,
      ),
      dict( # CELL2
        uldl_config=2,    rf_port=1,        n_antenna_dl=4,  n_antenna_ul=2,
        dl_earfcn=40200,  ul_earfcn=40200,
        n_rb_dl=50,
        cell_id=0x2,      n_id_cell=0x12,   tac=0x102,
        root_sequence_index=102,  inactivity_timer=1002,
      ),
    ])

    assertMatch(t, t.enb_cfg['nr_cell_list'],  [
      dict( # CELL3
        tdd_ul_dl_config=NO, rf_port=2,           n_antenna_dl=4,       n_antenna_ul=2,
        dl_nr_arfcn=300300,  ul_nr_arfcn=290700,  ssb_nr_arfcn=300270,  band=74,
        bandwidth=15,
        cell_id=0x3,         n_id_cell=0x13,      tac=NO,
        root_sequence_index=103,  inactivity_timer=1003,
      ),

      dict( # CELL4
        tdd_ul_dl_config={'pattern1': dict(
            period=5, dl_slots=7, dl_symbols=6, ul_slots=2, ul_symbols=4,
        )},
                             rf_port=3,           n_antenna_dl=4,       n_antenna_ul=2,
        dl_nr_arfcn=470400,  ul_nr_arfcn=470400,  ssb_nr_arfcn=470430,  band=40,
        bandwidth=20,
        cell_id=0x4,         n_id_cell=0x14,      tac=NO,
        root_sequence_index=104,  inactivity_timer=1004,
      ),
    ])


  # Carrier Aggregation
  def test_enb_cfg_ca(t):
    assertMatch(t, t.enb_cfg['cell_list'],  [
      { # CELL1
        'scell_list':           [{'cell_id': 2}],                   # LTE + LTE
        'en_dc_scg_cell_list':  [{'cell_id': 3}, {'cell_id': 4}],   # LTE + NR
      },
      { # CELL2
        'scell_list':           [{'cell_id': 1}],                   # LTE + LTE
        'en_dc_scg_cell_list':  [{'cell_id': 3}, {'cell_id': 4}],   # LTE + NR
      },
    ])

    assertMatch(t, t.enb_cfg['nr_cell_list'], [
      { # CELL3
        'scell_list':           [{'cell_id': 4}],                   # NR  + NR
      },
      { # CELL4
        'scell_list':           [{'cell_id': 3}],                   # NR  + NR
      },
    ])


  # Handover
  def test_enb_cfg_ho(t):
    assertMatch(t, t.enb_cfg['cell_list'],  [
      { # CELL1
        'ncell_list':   [
          dict(rat='eutra', cell_id= 0x1702, n_id_cell=0x12, dl_earfcn=40200, tac=0x102), # CELL2
          dict(rat='nr',    cell_id=      3),                                             # CELL3
          dict(rat='nr',    cell_id=      4),                                             # CELL4
        ] + t.ho_inter,
      },
      { # CELL2
        'ncell_list':   [
          dict(rat='eutra', cell_id= 0x1701, n_id_cell=0x11, dl_earfcn=  100, tac=0x101), # CELL1
          dict(rat='nr',    cell_id=      3),                                             # CELL3
          dict(rat='nr',    cell_id=      4),                                             # CELL4
        ] + t.ho_inter,
      },
    ])
    assertMatch(t, t.enb_cfg['nr_cell_list'], [
      { # CELL3
        'ncell_list':   [
          dict(rat='eutra', cell_id= 0x1701, n_id_cell=0x11, dl_earfcn=  100, tac=0x101), # CELL1
          dict(rat='eutra', cell_id= 0x1702, n_id_cell=0x12, dl_earfcn=40200, tac=0x102), # CELL2
          dict(rat='nr',    cell_id=      4),                                             # CELL4
        ] + t.ho_inter,
      },
      { # CELL4
        'ncell_list':   [
          dict(rat='eutra', cell_id= 0x1701, n_id_cell=0x11, dl_earfcn=  100, tac=0x101), # CELL1
          dict(rat='eutra', cell_id= 0x1702, n_id_cell=0x12, dl_earfcn=40200, tac=0x102), # CELL2
          dict(rat='nr',    cell_id=      3),                                             # CELL3
        ] + t.ho_inter,
      },
    ])


# ---- RU mixins to be used with RFTestCase4 ----

# SDR4 is mixin to verify SDR driver wrt all LTE/NR x FDD/TDD modes.
class SDR4:
  @classmethod
  def RUcfg(cls, i):
    return {
        'ru_type':      'sdr',
        'ru_link_type': 'sdr',
        'sdr_dev_list': [2*i,2*i+1],
    }

  # radio units configuration
  def test_rf_cfg_ru(t):
    assertMatch(t, t.rf_cfg['rf_driver'],  dict(
      name='sdr',
      args='dev0=/dev/sdr2,dev1=/dev/sdr3,dev2=/dev/sdr4,dev3=/dev/sdr5,' +
           'dev4=/dev/sdr6,dev5=/dev/sdr7,dev6=/dev/sdr8,dev7=/dev/sdr9',
      cpri_mapping=NO,
      cpri_mult=NO,
      cpri_rx_delay=NO,
      cpri_tx_delay=NO,
      cpri_tx_dbm=NO,
    ))


# Lopcomm4 is mixin to verify Lopcomm driver wrt all LTE/NR x FDD/TDD modes.
class Lopcomm4:
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

  # radio units configuration in enb.cfg
  def test_rf_cfg_ru(t):
    assertMatch(t, t.rf_cfg['rf_driver'],  dict(
      name='sdr',
      args='dev0=/dev/sdr0@1,dev1=/dev/sdr0@2,dev2=/dev/sdr0@3,dev3=/dev/sdr0@4',
      cpri_mapping='hw,hw,hw,hw',
      cpri_mult='4,4,4,4',
      cpri_rx_delay='41,42,43,44',
      cpri_tx_delay='51,52,53,54',
      cpri_tx_dbm='61,62,63,64',
    ))

  # RU configuration in cu_config.xml
  def test_ru_cu_config_xml(t):
    def uctx(rf_mode, cell_type, dl_arfcn, ul_arfcn, bw, dl_freq, ul_freq, tx_gain, rx_gain):
      return {
          'tx-array-carriers': {
            'rw-duplex-scheme':              rf_mode,
            'rw-type':                       cell_type,
            'absolute-frequency-center':    '%d' % dl_arfcn,
            'center-of-channel-bandwidth':  '%d' % dl_freq,
            'channel-bandwidth':            '%d' % bw,
            'gain':                         '%d' % tx_gain,
            'active':                       'ACTIVE',
          },
          'rx-array-carriers': {
            'absolute-frequency-center':    '%d' % ul_arfcn,
            'center-of-channel-bandwidth':  '%d' % ul_freq,
            'channel-bandwidth':            '%d' % bw,
            # XXX no rx_gain
            'active':                       'ACTIVE',
          },
      }

    _ = t._test_ru_cu_config_xml

    #       rf_mode  ctype dl_arfcn ul_arfcn   bw      dl_freq     ul_freq     txg rxg
    _(1, uctx('FDD', 'LTE',    100,   18100,  5000000, 2120000000, 1930000000, 11, 21))
    _(2, uctx('TDD', 'LTE',  40200,   40200, 10000000, 2551000000, 2551000000, 12, 22))
    _(3, uctx('FDD',  'NR', 300300,  290700, 15000000, 1501500000, 1453500000, 13, 23))
    _(4, uctx('TDD',  'NR', 470400,  470400, 20000000, 2352000000, 2352000000, 14, 24))

  def _test_ru_cu_config_xml(t, i, uctx):
    cu_xml = t.ipath('etc/%s' % xbuildout.encode('%s-cu_config.xml' % t.ref('RU%d' % i)))
    with open(cu_xml, 'r') as f:
      cu = f.read()
    cu = xmltodict.parse(cu)

    assertMatch(t, cu, {
      'xc:config': {
        'user-plane-configuration': {
          'tx-endpoints': [
            {'name': 'TXA0P00C00', 'e-axcid': {'eaxc-id': '0'}},
            {'name': 'TXA0P00C01', 'e-axcid': {'eaxc-id': '1'}},
            {'name': 'TXA0P01C00', 'e-axcid': {'eaxc-id': '2'}},
            {'name': 'TXA0P01C01', 'e-axcid': {'eaxc-id': '3'}},
          ],
          'tx-links': [
            {'name': 'TXA0P00C00', 'tx-endpoint': 'TXA0P00C00'},
            {'name': 'TXA0P00C01', 'tx-endpoint': 'TXA0P00C01'},
            {'name': 'TXA0P01C00', 'tx-endpoint': 'TXA0P01C00'},
            {'name': 'TXA0P01C01', 'tx-endpoint': 'TXA0P01C01'},
          ],
          'rx-endpoints': [
            {'name': 'RXA0P00C00',   'e-axcid': {'eaxc-id': '0'}},
            {'name': 'PRACH0P00C00', 'e-axcid': {'eaxc-id': '8'}},
            {'name': 'RXA0P00C01',   'e-axcid': {'eaxc-id': '1'}},
            {'name': 'PRACH0P00C01', 'e-axcid': {'eaxc-id': '24'}},
          ],
          'rx-links': [
            {'name': 'RXA0P00C00',   'rx-endpoint': 'RXA0P00C00'},
            {'name': 'PRACH0P00C00', 'rx-endpoint': 'PRACH0P00C00'},
            {'name': 'RXA0P00C01',   'rx-endpoint': 'RXA0P00C01'},
            {'name': 'PRACH0P00C01', 'rx-endpoint': 'PRACH0P00C01'},
          ],
        } | uctx
      }
    })


# Sunwave4 is mixin to verify Sunwave driver wrt all LTE/NR x FDD/TDD modes.
class Sunwave4:
  @classmethod
  def RUcfg(cls, i):
    return {
        'ru_type':      'sunwave',
        'ru_link_type': 'cpri',
        'cpri_link':    {
            'sdr_dev':  1,
            'sfp_port': i,
            'mult':     5,
            'mapping':  'bf1',
            'rx_delay': 140+i,
            'tx_delay': 150+i,
            'tx_dbm':   160+i
        },
        'mac_addr':     '00:FA:FE:00:00:%02x' % i,
    }

  # radio units configuration in enb.cfg
  def test_rf_cfg_ru(t):
    assertMatch(t, t.rf_cfg['rf_driver'],  dict(
      name='sdr',
      args='dev0=/dev/sdr1@1,dev1=/dev/sdr1@2,dev2=/dev/sdr1@3,dev3=/dev/sdr1@4',
      cpri_mapping='bf1,bf1,bf1,bf1',
      cpri_mult='5,5,5,5',
      cpri_rx_delay='141,142,143,144',
      cpri_tx_delay='151,152,153,154',
      cpri_tx_dbm='161,162,163,164',
    ))

# RUMultiType4 is mixin to verify that different RU types can be used at the same time.
class RUMultiType4:
  # ENB does not support mixing SDR + CPRI - verify only with CPRI-based units
  # see https://support.amarisoft.com/issues/26021 for details
  @classmethod
  def RUcfg(cls, i):
    assert 1 <= i <= 4, i
    if i in (1,2):
      return Lopcomm4.RUcfg(i)
    else:
      return Sunwave4.RUcfg(i)

  # radio units configuration in enb.cfg
  def test_rf_cfg_ru(t):
    assertMatch(t, t.rf_cfg['rf_driver'],  dict(
      name='sdr',
      args='dev0=/dev/sdr0@1,dev1=/dev/sdr0@2,dev2=/dev/sdr1@3,dev3=/dev/sdr1@4',
      cpri_mapping='hw,hw,bf1,bf1',
      cpri_mult='4,4,5,5',
      cpri_rx_delay='41,42,143,144',
      cpri_tx_delay='51,52,153,154',
      cpri_tx_dbm='61,62,163,164',
    ))


# instantiate eNB tests
class TestENB_SDR4        (ENBTestCase4, SDR4):         pass
class TestENB_Lopcomm4    (ENBTestCase4, Lopcomm4):     pass
class TestENB_Sunwave4    (ENBTestCase4, Sunwave4):     pass
class TestENB_RUMultiType4(ENBTestCase4, RUMultiType4): pass


# ---- UEsim ----

# UEsimTestCase4 provides base class for unit-testing UEsim service.
#
# It is similar to ENBTestCase4 but configures UE cells instead of eNB cells.
class UEsimTestCase4(RFTestCase4):
  @classmethod
  def getInstanceSoftwareType(cls):
    return "ue"

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.ue_cfg = cls.rf_cfg = yamlpp_load(cls.ipath('etc/ue.cfg'))

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps({
        'testing':      True,
    })}

  @classmethod
  def CELLcfg(cls, i):
    return CUE

  @classmethod
  def requestAllShared(cls, imain):
    super().requestAllShared(imain)

    def UE(i):
      ue = {
          'ue_type':  ('lte', 'nr') [(i-1) % 2],
          'rue_addr': 'host%d'    % i,
          'sim_algo': ('xor', 'milenage', 'tuak') [i-1],
          'imsi':     '%015d'     % i,
          'opc':      '%032x'     % i,
          'amf':      '0x%04x'    % (0x9000+i),
          'sqn':      '%012x'     % i,
          'k':        'FFFF%028x' % i,
          'impi':     'impi%d@rapid.space' % i,
      }
      return cls.requestShared(imain, 'UE%d' % i, ue)

    UE(1)
    UE(2)
    UE(3)

  # ue parameters
  def test_ue_cfg_ue(t):
    assertMatch(t, t.ue_cfg['ue_list'], [
      dict(
        as_release=13,  ue_category=13,   rue_addr='host1',
        sim_algo='xor', amf =0x9001,      impi='impi1@rapid.space',
        sqn ='000000000001',
        imsi='000000000000001',
        opc ='00000000000000000000000000000001',
        K   ='FFFF0000000000000000000000000001',
      ),
      dict(
        as_release=15,  ue_category='nr', rue_addr='host2',
        sim_algo='milenage', amf =0x9002, impi='impi2@rapid.space',
        sqn ='000000000002',
        imsi='000000000000002',
        opc ='00000000000000000000000000000002',
        K   ='FFFF0000000000000000000000000002',
      ),
      dict(
        as_release=13,  ue_category=13,   rue_addr='host3',
        sim_algo='tuak', amf =0x9003,     impi='impi3@rapid.space',
        sqn ='000000000003',
        imsi='000000000000003',
        opc ='00000000000000000000000000000003',
        K   ='FFFF0000000000000000000000000003',
      ),
    ])

  # cells
  def test_ue_cfg_cell(t):
    assertMatch(t, t.ue_cfg['cell_groups'], [
      dict(
        group_type='lte',
        cells=[
          dict( # CELL1
            rf_port=0,        n_antenna_dl=4,  n_antenna_ul=2,
            dl_earfcn=100,    ul_earfcn=18100,
            bandwidth=5,
          ),
          dict( # CELL2
            rf_port=1,        n_antenna_dl=4,  n_antenna_ul=2,
            dl_earfcn=40200,  ul_earfcn=40200,
            bandwidth=10,
          ),
        ]
      ),
      dict(
        group_type='nr',
        cells=[
          dict( # CELL3
            rf_port=2,           n_antenna_dl=4,      n_antenna_ul=2,
            dl_nr_arfcn=300300,  ul_nr_arfcn=290700,  ssb_nr_arfcn=300270,  band=74,
            bandwidth=15,
          ),
          dict( # CELL4
            rf_port=3,           n_antenna_dl=4,      n_antenna_ul=2,
            dl_nr_arfcn=470400,  ul_nr_arfcn=470400,  ssb_nr_arfcn=470430,  band=40,
            bandwidth=20,
          ),
        ]
      )
    ])


# instantiate UEsim tests
class TestUEsim_SDR4        (UEsimTestCase4, SDR4):         pass
class TestUEsim_Lopcomm4    (UEsimTestCase4, Lopcomm4):     pass
class TestUEsim_Sunwave4    (UEsimTestCase4, Sunwave4):     pass
class TestUEsim_RUMultiType4(UEsimTestCase4, RUMultiType4): pass


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

class TestAssertMatch(unittest.TestCase):
  def test_assertMatch(t):
    y, n = True, False
    testv = [   # [](match, v, vok)
        (y, 12,  12),
        (n, 12,  13),
        (n, 12,  '12'),
        (y, 'a', 'a'),
        (n, 'a', 'ab'),
        (y, [],  []),
        (n, [],  [1]),
        (y, [1], [1]),
        (n, [1,2], [1]),
        (y, [1,2], [1,2]),
        (n, [1,2], ['a',2]),
        (y, {}, {}),
        (y, {'a': 1}, {}),
        (y, {'a': 1}, {'a': 1}),
        (n, {'a': 1}, {'a': 2}),
        (n, {'a': 1}, {'a': NO}),
        (y, {},       {'a': NO}),
        (y, {'b': 2}, {'a': NO}),
        (n, {'a': 1, 'b': 2}, {'a': NO}),
        (n, {'a': 1, 'b': 2}, {'a': NO, 'b': 2}),
        (y, {'a': 1, 'b': 2}, {         'b': 2}),
        (y, {'a': [1, 2, {'aa': 33, 'bb': 44}]},
            {'a': [1, 2, {'aa': 33, 'cc': NO}]}),
        (n, {'a': [1, 2, {'aa': 33, 'bb': 44}]},
            {'a': [1, 2, {'aa': 35, 'cc': NO}]}),
    ]

    for mok, v, vok in testv:
      with t.subTest(mok=mok, v=v, vok=vok):
        if mok:
          assertMatch(t, v, vok)
        else:
          t.assertRaises(t.failureException,
              assertMatch, t, v, vok)


# hide base TestCases from unittest discovery so that their test_ methods are
# run only on leaf test classes.
def __dir__():
  d = list(sorted(globals().keys()))
  abstract = {'AmariTestCase', 'RFTestCase4', 'ENBTestCase4', 'UEsimTestCase4'}
  for _ in abstract:
    d.remove(_)
  return d
