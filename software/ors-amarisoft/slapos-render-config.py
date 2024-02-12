# Program slapos-render-config is handy during config/ templates development.
#
# It mimics the way config files are generated during the build but runs much
# faster compared to full `slapos node software` + `slapos node instance` runs.

import zc.buildout.buildout # XXX workaround for https://lab.nexedi.com/nexedi/slapos.recipe.template/merge_requests/9
from slapos.recipe.template import jinja2_template

import json, copy, sys, os, pprint, shutil

sys.path.insert(0, './ru')
import xbuildout

B = xbuildout.encode


# j2render renders config/<src> into config/out/<out> with provided json parameters.
def j2render(src, out, jcfg):
    src = 'config/{}'.format(src)
    out = 'config/out/{}'.format(out)

    ctx = json.loads(jcfg)
    assert '_standalone' not in ctx
    ctx['_standalone'] = True
    ctx.setdefault('ors', False)
    textctx = ''
    for k, v in ctx.items():
        textctx += 'json %s %s\n' % (k, json.dumps(v))
    textctx += 'import xbuildout xbuildout\n'
    textctx += 'import json_module    json\n'
    textctx += 'import nrarfcn_module nrarfcn\n'
    textctx += 'import xearfcn_module  xlte.earfcn\n'
    textctx += 'import xnrarfcn_module xlte.nrarfcn\n'
    buildout = None # stub
    r = jinja2_template.Recipe(buildout, "recipe", {
      'extensions': 'jinja2.ext.do',
      'url': src,
      'output': out,
      'context': textctx,
      'import-list': '''
        rawfile slaplte.jinja2 slaplte.jinja2''',
      })
    #print(r.context)

    # avoid dependency on zc.buildout.download and the need to use non-stub buildout section
    def _read(url, *args):
        with open(url, *args) as f:
            return f.read()
    r._read = _read

    # for template debugging
    r.context.update({
        'print':  lambda *argv:  print(*argv, file=sys.stderr),
        'pprint': lambda obj:    pprint.pprint(obj, sys.stderr),
    })

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w+') as f:
      f.write(r._render().decode())


# Instance simulates configuration for an instance on SlapOS Master.
class Instance:
    def __init__(self, slap_software_type):
        self.shared_instance_list = []
        self.slap_software_type = slap_software_type

    # ishared appends new shared instance with specified configuration to .shared_instance_list .
    def ishared(self, slave_reference, cfg):
        ishared = {
            # see comments in jref_of_shared about where and how slapproxy and
            # slapos master put partition_reference of a shared instance.
            'slave_title':          '_%s' % slave_reference,
            'slave_reference':      'SOFTINST-%03d' % (len(self.shared_instance_list)+1),
            'slap_software_type':   self.slap_software_type,
            '_': json.dumps(cfg)
        }
        self.shared_instance_list.append(ishared)
        return ishared

# py version of jref_of_shared (simplified).
def ref_of_shared(ishared):
    ref = ishared['slave_title']
    ref = ref.removeprefix('_')
    return ref


# ---- eNB ----

# 3 cells sharing SDR-based RU consisting of 2 SDR boards (4tx + 4rx ports max)
# RU definition is embedded into cell for simplicity of management
def iRU1_SDR_tLTE2_tNR(ienb):
    RU = {
        'ru_type':      'sdr',
        'ru_link_type': 'sdr',
        'sdr_dev_list': [0, 1],
        'n_antenna_dl': 4,
        'n_antenna_ul': 2,
        'tx_gain':      51,
        'rx_gain':      52,
    }

    ienb.ishared('CELL_a', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'bandwidth':    5,
        'dl_earfcn':    38050,      # 2600 MHz
        'pci':          1,
        'cell_id':      '0x01',
        'tac':          '0x1234',
        'ru':           RU,         # RU definition embedded into CELL
    })

    ienb.ishared('CELL_b', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'bandwidth':    5,
        'dl_earfcn':    38100,      # 2605 MHz
        'pci':          2,
        'cell_id':      '0x02',
        'tac':          '0x1234',
        'ru':           {           # CELL_b shares RU with CELL_a referring to it via cell
            'ru_type':      'ruincell_ref',
            'ruincell_ref': 'CELL_a'
        }
    })

    ienb.ishared('CELL_c', {
        'cell_type':    'nr',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'bandwidth':    10,
        'dl_nr_arfcn':  523020,     # 2615.1 MHz
        'nr_band':      41,
        'pci':          3,
        'cell_id':      '0x03',
        'tac':          '0x1234',
        'ru':           {
            'ru_type':      'ruincell_ref',     # CELL_c shares RU with CELL_a and CELL_b
            'ruincell_ref': 'CELL_b'            # referring to RU via CELL_b -> CELL_a
        }
    })


# LTE + NR cells using 2 RU each consisting of SDR.
# here we instantiate RUs separately since embedding RU into a cell is demonstrated by CELL_a above
#
# NOTE: if we would want to share the RU by LTE/tdd and NR/tdd cells, we would
#       need to bring their TDD configuration to match each other exactly.
def iRU2_SDR_tLTE_tNR(ienb):
    RU1 = {
        'ru_type':      'sdr',
        'ru_link_type': 'sdr',
        'sdr_dev_list': [1],
        'n_antenna_dl': 2,
        'n_antenna_ul': 1,
        'tx_gain':      51,
        'rx_gain':      52,
        'txrx_active':  'ACTIVE',
    }

    RU2 = copy.deepcopy(RU1)
    RU2['sdr_dev_list'] = [2]

    ienb.ishared('RU1', RU1)
    ienb.ishared('RU2', RU2)

    ienb.ishared('CELL_a', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'bandwidth':    5,
        'dl_earfcn':    38050,      # 2600 MHz
        'pci':          1,
        'cell_id':      '0x01',
        'tac':          '0x1234',
        'ru':           {           # CELL_a links to RU1 by its reference
            'ru_type':  'ru_ref',
            'ru_ref':   'RU1'
        }
    })

    ienb.ishared('CELL_b', {
        'cell_type':    'nr',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'bandwidth':    10,
        'dl_nr_arfcn':  523020,     # 2615.1 MHz
        'nr_band':      41,
        'pci':          2,
        'cell_id':      '0x02',
        'tac':          '0x1234',
        'ru':           {
            'ru_type':  'ru_ref',
            'ru_ref':   'RU2'
        }
    })


# LTE + NR cells that use CPRI-based Lopcomm radio units
def iRU2_LOPCOMM_fLTE_fNR(ienb):
    RU1 = {
        'ru_type':      'lopcomm',
        'ru_link_type': 'cpri',
        'mac_addr':     '00:00:00:00:00:01',
        'cpri_link':    {
            'sdr_dev':  2,
            'sfp_port': 0,
            'mult':     8,
            'mapping':  'standard',
            'rx_delay': 10,
            'tx_delay': 11,
            'tx_dbm':   50
        },
        'n_antenna_dl': 2,
        'n_antenna_ul': 1,
        'tx_gain':      -21,
        'rx_gain':      -22,
    }

    RU2 = copy.deepcopy(RU1)
    RU2['mac_addr'] = '00:00:00:00:00:02'
    RU2['cpri_link']['sfp_port'] = 1
    RU2['tx_gain'] += 10
    RU2['rx_gain'] += 10

    ienb.ishared('RU1', RU1)
    ienb.ishared('RU2', RU2)

    ienb.ishared('CELL_a', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'fdd',
        'bandwidth':    5,
        'dl_earfcn':    3350,       # 2680 MHz
        'pci':          21,
        'cell_id':      '0x21',
        'tac':          '0x1234',
        'ru':           {
            'ru_type':  'ru_ref',
            'ru_ref':   'RU1'
        }
    })

    ienb.ishared('CELL_b', {
        'cell_type':    'nr',
        'cell_kind':    'enb',
        'rf_mode':      'fdd',
        'bandwidth':    5,
        'dl_nr_arfcn':  537200,     # 2686 MHz
        'nr_band':      7,
        'pci':          22,
        'cell_id':      '0x22',
        'tac':          '0x1234',
        'ru':           {
            'ru_type':  'ru_ref',
            'ru_ref':   'RU2'
        }
    })


# ---- for tests ----

# 2 FDD cells working via shared SDR board
def iRU1_SDR1_fLTE2(ienb):
    RU = {
        'ru_type':      'sdr',
        'ru_link_type': 'sdr',
        'sdr_dev_list': [1],
        'n_antenna_dl': 1,
        'n_antenna_ul': 1,
        'tx_gain':      67,
        'rx_gain':      61,
    }

    ienb.ishared('CELL_a', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'fdd',
        'bandwidth':    5,
        'dl_earfcn':    3350,      # 2680 MHz (Band 7)
        'pci':          1,
        'cell_id':      '0x01',
        'tac':          '0x1234',
        'ru':           RU,
    })

    ienb.ishared('CELL_b', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'fdd',
        'bandwidth':    5,
        'dl_earfcn':    3050,      # 2650 MHz (Band 7)
        'pci':          1,
        'cell_id':      '0x02',
        'tac':          '0x1234',
        'ru':           {
            'ru_type':      'ruincell_ref',
            'ruincell_ref': 'CELL_a'
        }
    })

def iRU2_LOPCOMM_fLTE2(ienb):
    # supports: 2110 - 2170 MHz
    RU_0002 = {
        'ru_type':      'lopcomm',
        'ru_link_type': 'cpri',
        'mac_addr':     '00:00:00:00:00:01',
        'cpri_link':    {
            'sdr_dev':  0,
            'sfp_port': 0,
            'mult':     8,
            'mapping':  'hw',
            'rx_delay': 25.11,
            'tx_delay': 14.71,
            'tx_dbm':   63
        },
        'n_antenna_dl': 1,
        'n_antenna_ul': 1,
        'tx_gain':      0,
        'rx_gain':      0,
    }

    # supports: 2110 - 2170 MHz
    RU_0004 = copy.deepcopy(RU_0002)
    RU_0004['mac_addr'] = '00:00:00:00:00:04'
    RU_0004['cpri_link']['sfp_port'] = 1

    if 1:
        ienb.ishared('RU_0002', RU_0002)
        ienb.ishared('CELL2', {
            'cell_type':    'lte',
            'cell_kind':    'enb',
            'rf_mode':      'fdd',
            'bandwidth':    20,
            'dl_earfcn':    100,        # 2120 MHz   @ B1
            'pci':          21,
            'cell_id':      '0x21',
            'tac':          '0x1234',
            'ru':           {
                'ru_type':  'ru_ref',
                'ru_ref':   'RU_0002'
            }
        })

    if 1:
        ienb.ishared('RU_0004', RU_0004)
        ienb.ishared('CELL4', {
            'cell_type':    'lte',
            'cell_kind':    'enb',
            'rf_mode':      'fdd',
            'bandwidth':    20,
            'dl_earfcn':    500,        # 2160 MHz  @ B1
            'pci':          22,
            'cell_id':      '0x22',
            'tac':          '0x1234',
            'ru':           {
                'ru_type':  'ru_ref',
                'ru_ref':   'RU_0004'
            }
        })

# ORS_eNB and ORS_gNB mimic what instance-ors-enb.jinja2.cfg does.
ORS_ru = {
    'ru_type':      'sdr',
    'ru_link_type': 'sdr',
    'sdr_dev_list': [0],
    'n_antenna_dl': 2,
    'n_antenna_ul': 2,
    'tx_gain':      62,
    'rx_gain':      43,
}
ORS_json = """
    "ors": {"one-watt": true},
"""
def ORS_enb(ienb):
    ienb.ishared('RU', ORS_ru)
    ienb.ishared('CELL', {
        'cell_type':    'lte',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'dl_earfcn':    36100,
        'bandwidth':    10,
        'tac':          '0x0001',
        'root_sequence_index': 204,
        'pci':          1,
        'cell_id':      '0x01',
        "tdd_ul_dl_config": "[Configuration 6] 5ms 5UL 3DL (maximum uplink)",
        'inactivity_timer': 10000,
        'ru': {
            'ru_type': 'ru_ref',
            'ru_ref':  'RU',
        },
    })
    return {'out': 'ors/enb', 'jextra': ORS_json, 'want_nr': False}

def ORS_gnb(ienb):
    ienb.ishared('RU', ORS_ru)
    ienb.ishared('CELL', {
        'cell_type':    'nr',
        'cell_kind':    'enb',
        'rf_mode':      'tdd',
        'dl_nr_arfcn':  380000,
        'nr_band':      39,
        'bandwidth':    40,
        'ssb_pos_bitmap': "10000000",
        'root_sequence_index':  1,
        'pci':          500,
        'cell_id':      '0x01',
        "tdd_ul_dl_config": "5ms 8UL 1DL 2/10 (maximum uplink)",
        'inactivity_timer': 10000,
        'ru': {
            'ru_type': 'ru_ref',
            'ru_ref':  'RU',
        },
    })
    return {'out': 'ors/gnb', 'jextra': ORS_json, 'want_lte': False}

def do_enb():
    for f in (iRU1_SDR_tLTE2_tNR,
              iRU2_SDR_tLTE_tNR,
              iRU2_LOPCOMM_fLTE_fNR,
              iRU1_SDR1_fLTE2,
              iRU2_LOPCOMM_fLTE2,
              ORS_enb,
              ORS_gnb):
        _do_enb_with(f)

def _do_enb_with(iru_icell_func):
    ienb = Instance('enb')
    opt = iru_icell_func(ienb)  or  {}
    out = opt.get('out', 'enb/%s' % iru_icell_func.__name__)
    want_lte = opt.get('want_lte', True)
    want_nr  = opt.get('want_nr',  True)

    # add 4 peer nodes
    if want_lte:
        ienb.ishared('PEER11', {
            'peer_type':    'lte',
            'x2_addr':      '44.1.1.1',
        })
        ienb.ishared('PEER12', {
            'peer_type':    'lte',
            'x2_addr':      '44.1.1.2',
        })
    if want_nr:
        ienb.ishared('PEER21', {
            'peer_type':    'nr',
            'xn_addr':      '55.1.1.1',
        })
        ienb.ishared('PEER22', {
            'peer_type':    'nr',
            'xn_addr':      '55.1.1.2',
        })

    # add 2 peer cells
    if want_lte:
        ienb.ishared('PEERCELL1', {
            'cell_type':        'lte',
            'cell_kind':        'enb_peer',
            'e_cell_id':        '0x12345',
            'pci':              35,
            'dl_earfcn':        700,
            'tac':              123,
        })
    if want_nr:
        ienb.ishared('PEERCELL2', {
            'cell_type':        'nr',
            'cell_kind':        'enb_peer',
            'nr_cell_id':       '0x77712',
            'gnb_id_bits':      22,
            'dl_nr_arfcn':      520000,
            'nr_band':          38,
            'pci':              75,
            'tac':              321,
        })

    jshared_instance_list = json.dumps(ienb.shared_instance_list)
    jextra = opt.get('jextra', '')
    json_params = """{
        %(jextra)s
        "sib23_file": "sib2_3.asn",
        "slap_configuration": {
            "tap-name": "slaptap9",
            "slap-computer-partition-id": "slappart9",
            "slave-instance-list": %(jshared_instance_list)s
        },
        "directory": {
            "log": "log",
            "etc": "etc",
            "var": "var"
        },
        "slapparameter_dict": {
            "enb_id": "0x1A2D0",
            "gnb_id": "0x12345",
            "gnb_id_bits": 28,
            "com_ws_port": 9001,
            "com_addr": "127.0.1.2",
            "gtp_addr":     "127.0.1.1",
            "mme_list":     {"1": {"mme_addr": "127.0.1.100"}},
            "amf_list":     {"1": {"amf_addr": "127.0.1.100"}},
            "plmn_list":    {"1": {"plmn": "00101"}},
            "plmn_list_5g": {"1": {"plmn": "00101", "tac": 100}},
            "nssai":        {"1": {"sst": 1}}
        }
    }""" % locals()

    j2render('enb.jinja2.cfg', '%s/enb.cfg' % out, json_params)

    # drb.cfg + sib.asn for all cells
    iru_dict       = {}
    icell_dict     = {}
    ipeer_dict     = {}
    ipeercell_dict = {}
    for ishared in ienb.shared_instance_list:
        ref = ref_of_shared(ishared)
        _   = json.loads(ishared['_'])
        ishared['_'] = _
        if 'ru_type' in _:
            iru_dict[ref] = ishared
        elif 'cell_type' in _  and  _.get('cell_kind') in {'enb', 'enb_peer'}:
            idict = {'enb': icell_dict, 'enb_peer': ipeercell_dict} [_['cell_kind']]
            idict[ref] = ishared
        elif 'peer_type' in _:
            ipeer_dict[ref] = ishared
        else:
            raise AssertionError('enb: unknown shared instance %r' % (ishared,))

    def ru_of_cell(icell): # -> (ru_ref, ru)
        cell_ref = ref_of_shared(icell)
        ru = icell['_']['ru']
        if ru['ru_type'] == 'ru_ref':
            ru_ref = ru['ru_ref']
            return ru_ref, iru_dict[ru_ref]
        elif ru['ru_type'] == 'ruincell_ref':
            return ru_of_cell(icell_dict[ru['ruincell_ref']])
        else:
            return ('_%s_ru' % cell_ref), ru  # embedded ru definition

    for cell_ref, icell in icell_dict.items():
        ru_ref, ru = ru_of_cell(icell)
        cell = icell['_']
        jctx = json.dumps({
                    'cell_ref': cell_ref,
                    'cell':     cell,
                    'ru_ref':   ru_ref,
                    'ru':       ru,
               })
        j2render('drb_%s.jinja2.cfg' % cell['cell_type'],
                 '%s/%s-drb.cfg' % (out, B(cell_ref)),
                 jctx)

        j2render('sib23.jinja2.asn',
                 '%s/%s-sib23.asn' % (out, B(cell_ref)),
                 jctx)


# ---- UE ----

def do_ue():
    def do(src, out, slapparameter_dict):
        jslapparameter_dict = json.dumps(slapparameter_dict)
        json_params = """{
            "slap_configuration": {
                "tap-name": "slaptap9"
            },
            "directory": {
                "log": "log",
                "etc": "etc",
                "var": "var"
            },
            "pub_info": {
                "rue_bind_addr": "::1",
                "com_addr": "[::1]:9002"
            },
            "slapparameter_dict": %(jslapparameter_dict)s
        }"""
        j2render(src, out, json_params % locals())

    do('ue.jinja2.cfg', 'ue-lte.cfg', {'ue_type': 'lte', 'rue_addr': 'host1'})
    do('ue.jinja2.cfg',  'ue-nr.cfg', {'ue_type':  'nr', 'rue_addr': 'host2'})


def main():
    if os.path.exists('config/out'):
        shutil.rmtree('config/out')
    do_enb()
    do_ue()


if __name__ == '__main__':
    main()
