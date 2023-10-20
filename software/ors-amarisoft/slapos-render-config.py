# Program slapos-render-config is handy during config/ templates development.
#
# It mimics the way config files are generated during the build but runs much
# faster compared to full `slapos node software` + `slapos node instance` runs.

import zc.buildout.buildout # XXX workaround import bug in vvv
from slapos.recipe.template import jinja2_template

import json, copy, sys, os, pprint, glob


# j2render renders config/<src> into config/out/<out> with provided json parameters.
def j2render(src, out, jcfg):
    ctx = json.loads(jcfg)
    assert '_standalone' not in ctx
    ctx['_standalone'] = True
    textctx = ''
    for k, v in ctx.items():
        textctx += 'json %s %s\n' % (k, json.dumps(v))
    textctx += 'import json_module    json\n'
    textctx += 'import earfcn_module  xlte.earfcn\n'
    textctx += 'import nrarfcn_module nrarfcn\n'
    buildout = None # stub
    r = jinja2_template.Recipe(buildout, "recipe", {
      'extensions': 'jinja2.ext.do',
      'url': 'config/{}'.format(src),
      'output': 'config/out/{}'.format(out),
      'context': textctx,
      'import-list': '''
        rawfile amari_lte.jinja2  amari/lte.jinja2
        rawfile amari_slap.jinja2 amari/slap.jinja2''',
      })

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

    with open('config/out/{}'.format(out), 'w+') as f:
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
    RU1 = {
        'ru_type':      'sdr',
        'ru_link_type': 'sdr',
        'sdr_dev_list': [0, 1],
        'n_antenna_dl': 4,
        'n_antenna_ul': 2,
        'tx_gain':      51,
        'rx_gain':      52,
    }

    ienb.ishared('CELL1_a', {
        'cell_type':    'lte',
        'rf_mode':      'tdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    38050,      # 2600 MHz
        'pci':          1,
        'cell_id':      '0x01',
        'ru':           RU1,        # RU definition embedded into CELL
    })

    ienb.ishared('CELL1_b', {
        'cell_type':    'lte',
        'rf_mode':      'tdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    38100,      # 2605 MHz
        'pci':          2,
        'cell_id':      '0x02',
        'ru':           {           # CELL1_b shares RU with CELL1_a referring to it via cell
            'ru_type':      'ruincell_ref',
            'ruincell_ref': 'CELL1_a'
        }
    })

    ienb.ishared('CELL1_c', {
        'cell_type':    'nr',
        'rf_mode':      'tdd',
        'bandwidth':    5,
        'dl_nr_arfcn':  522000,     # 2610 MHz
        'nr_band':      38,
        'pci':          3,
        'cell_id':      '0x03',
        'ru':           {
            'ru_type':      'ruincell_ref',     # CELL1_c shares RU with CELL1_a and CELL1_b
            'ruincell_ref': 'CELL1_b'           # referring to RU via CELL1_b -> CELL1_a
        }
    })


# LTE + NR cells that use CPRI-based Lopcomm radio units
# here we instantiate RUs separately since embedding RU into a cell is demonstrated by CELL1_a above
def iRU2_LOPCOMM_fLTE_fNR(ienb):
    RU2_a = {
        'ru_type':      'lopcomm',
        'ru_link_type': 'cpri',
        'mac_addr':     'XXX',
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

    RU2_b = copy.deepcopy(RU2_a)
    RU2_b['mac_addr'] = 'YYY'
    RU2_b['cpri_link']['sfp_port'] = 1
    RU2_b['tx_gain'] += 10
    RU2_b['rx_gain'] += 10

    ienb.ishared('RU2_a', RU2_a)
    ienb.ishared('RU2_b', RU2_b)

    ienb.ishared('CELL2_a', {
        'cell_type':    'lte',
        'rf_mode':      'fdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    3350,       # 2680 MHz
        'pci':          21,
        'cell_id':      '0x21',
        'ru':           {           # CELL2_a links to RU2_a by its reference
            'ru_type':  'ru_ref',
            'ru_ref':   'RU2_a'
        }
    })

    ienb.ishared('CELL2_b', {
        'cell_type':    'nr',
        'rf_mode':      'fdd',
        'bandwidth':    5,
        'dl_nr_arfcn':  537200,     # 2686 MHz
        'nr_band':      7,
        'pci':          22,
        'cell_id':      '0x22',
        'ru':           {
            'ru_type':  'ru_ref',
            'ru_ref':   'RU2_b'
        }
    })


# ---- for tests ----

# 2 FDD cells working via shared SDR board
def iRU3_SDR1_fLTE2(ienb):
    RU = {
        'ru_type':      'sdr',
        'ru_link_type': 'sdr',
        'sdr_dev_list': [1],
        'n_antenna_dl': 1,
        'n_antenna_ul': 1,
        'tx_gain':      67,
        'rx_gain':      61,
    }

    ienb.ishared('CELL3_a', {
        'cell_type':    'lte',
        'rf_mode':      'fdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    3350,      # 2680 MHz (Band 7)
        'pci':          1,
        'cell_id':      '0x01',
        'ru':           RU,
    })

    ienb.ishared('CELL3_b', {
        'cell_type':    'lte',
        'rf_mode':      'fdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    3050,      # 2650 MHz (Band 7)
        'pci':          1,
        'cell_id':      '0x02',
        'ru':           {
            'ru_type':      'ruincell_ref',
            'ruincell_ref': 'CELL3_a'
        }
    })

def iRU2_LOPCOMM_fLTE2(ienb):
    # supports: 2110 - 2170 MHz
    RU_0002 = {
        'ru_type':      'lopcomm',
        'ru_link_type': 'cpri',
#       'mac_addr':     'XXX',
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
#   RU_0004['mac_addr'] = 'YYY'
    RU_0004['cpri_link']['sfp_port'] = 1

    if 1:
        ienb.ishared('RU_0002', RU_0002)
        ienb.ishared('CELL2', {
            'cell_type':    'lte',
            'rf_mode':      'fdd',
            'bandwidth':    '20 MHz',
            'dl_earfcn':    100,        # 2120 MHz   @ B1
            'pci':          21,
            'cell_id':      '0x21',
            'ru':           {
                'ru_type':  'ru_ref',
                'ru_ref':   'RU_0002'
            }
        })

    if 1:
        ienb.ishared('RU_0004', RU_0004)
        ienb.ishared('CELL4', {
            'cell_type':    'lte',
            'rf_mode':      'fdd',
            'bandwidth':    '20 MHz',
            'dl_earfcn':    500,        # 2160 MHz  @ B1
            'pci':          22,
            'cell_id':      '0x22',
            'ru':           {
                'ru_type':  'ru_ref',
                'ru_ref':   'RU_0004'
            }
        })

def do_enb():
    ienb = Instance('enb')
    iRU1_SDR_tLTE2_tNR(ienb)
    #iRU2_LOPCOMM_fLTE_fNR(ienb)
    #iRU3_SDR1_fLTE2(ienb)
    #iRU2_LOPCOMM_fLTE2(ienb)

    jshared_instance_list = json.dumps(ienb.shared_instance_list)
    json_params = """{
        "sib23_file": "sib2_3.asn",
        "slap_configuration": {
            "tap-name": "slaptap9",
            "slap-computer-partition-id": "slappart9",
            "configuration.default_lte_inactivity_timer": 10000,
            "configuration.default_nr_inactivity_timer": 10000,
            "slave-instance-list": %(jshared_instance_list)s
        },
        "directory": {
            "log": "log",
            "etc": "etc",
            "var": "var"
        },
        "slapparameter_dict": {
        }
    }""" % locals()

    j2render('enb.jinja2.cfg', 'enb.cfg', json_params)

    # drb.cfg + sib.asn for all cells
    iru_dict   = {}
    icell_dict = {}
    for ishared in ienb.shared_instance_list:
        ref = ref_of_shared(ishared)
        _   = json.loads(ishared['_'])
        ishared['_'] = _
        print(ref)
        if 'ru_type' in _:
            iru_dict[ref] = ishared
        elif 'cell_type' in _:
            icell_dict[ref] = ishared
        else:
            raise AssertionError('enb: unknown shared instance %r' % (ishared,))

    print()
    print(iru_dict)
    print(icell_dict)

    # ~ jcell_ru_ref (simplified).
    def ru_of_cell(icell):
        cell_ref = ref_of_shared(icell)
        ru = icell['_']['ru']
        if ru['ru_type'] == 'ru_ref':
            return iru_dict[ru.ru_ref]
        elif ru['ru_type'] == 'ruincell_ref':
            return ru_of_cell(icell_dict[ru['ruincell_ref']])
        else:
            # embedded ru definition
            return ru

    for cell_ref, icell in icell_dict.items():
        ru = ru_of_cell(icell)
        cell = icell['_']
        j2render('drb_%s.jinja2.cfg' % cell['cell_type'],
                 '%s-drb.cfg' % cell_ref,
                 json.dumps({
                     'cell_ref': cell_ref,
                     'cell':     cell,
                 }))

        j2render('sib23.jinja2.asn',
                 '%s-sib23.asn' % cell_ref,
                 json.dumps({
                     'cell_ref': cell_ref,
                     'cell':     cell,
                     'ru':       ru,
                 }))



# ---- UE ----

def do_ue():
    iue = Instance('ue')
    iue.ishared('UCELL1', {
        'ue_cell_type': 'lte',
        'rf_mode':      'tdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    38050,      # 2600 MHz
        'ru':           {
            'ru_type':      'sdr',
            'ru_link_type': 'sdr',
            'sdr_dev_list': [0],
            'n_antenna_dl': 2,
            'n_antenna_ul': 1,
            'tx_gain':      41,
            'rx_gain':      42,
        }
    })
    iue.ishared('UCELL2', {
        'ue_cell_type': 'nr',
        'rf_mode':      'fdd',
        'bandwidth':    5,
        'dl_nr_arfcn':  537200,     # 2686 MHz
        'nr_band':      7,
        'ru':           {           # NOTE contrary to eNB UEsim cannot share one RU in between several cells
            'ru_type':      'sdr',
            'ru_link_type': 'sdr',
            'sdr_dev_list': [2],
            'n_antenna_dl': 2,
            'n_antenna_ul': 2,
            'tx_gain':      31,
            'rx_gain':      32,
        }
    })

    iue.ishared('UE1', {
        'ue_type':      'lte',
        'rue_addr':     'host1'
    })
    iue.ishared('UE2', {
        'ue_type':      'nr',
        'rue_addr':     'host2'
    })

    jshared_instance_list = json.dumps(iue.shared_instance_list)
    json_params = """{
        "slap_configuration": {
            "tap-name": "slaptap9",
            "slap-computer-partition-id": "slappart9",
            "slave-instance-list": %(jshared_instance_list)s
        },
        "pub_info": {
            "rue_bind_addr": "::1",
            "com_addr": "[::1]:9002"
        },
        "directory": {
            "log": "log",
            "etc": "etc",
            "var": "var"
        },
        "slapparameter_dict": {
        }
    }""" % locals()

    j2render('ue.jinja2.cfg', 'ue.cfg', json_params)


def main():
    for f in glob.glob('config/out/*'):
        os.remove(f)
    do_enb()
    do_ue()


if __name__ == '__main__':
    main()
