# Program slapos-render-config is handy during config/ templates development.
#
# It mimics the way config files are generated during the build but runs much
# faster compared to full `slapos node software` + `slapos node instance` runs.

import zc.buildout.buildout # XXX workaround import bug in vvv
from slapos.recipe.template import jinja2_template

import json, copy, sys, pprint


# j2render renders config/<config>.jinja2.cfg into config/<config>.cfg with provided json parameters.
def j2render(config, jcfg):
    ctx = json.loads(jcfg)
    textctx = ''
    for k, v in ctx.items():
        textctx += 'json %s %s\n' % (k, json.dumps(v))
    textctx += 'import json_module json\n'
    buildout = None # stub
    r = jinja2_template.Recipe(buildout, "recipe", {
      'extensions': 'jinja2.ext.do',
      'url': 'config/{}.jinja2.cfg'.format(config),
      'output': 'config/{}.cfg'.format(config),
      'context': textctx,
      'import-list': 'rawfile lte.jinja2 config/lte.jinja2',
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

    with open('config/{}.cfg'.format(config), 'w+') as f:
      f.write(r._render().decode())


# Instance simulates configuration for an instance on SlapOS Master.
class Instance:
    def __init__(self):
        self.shared_instance_list = []

    # ishared appends new shared instance with specified configuration to .shared_instance_list .
    def ishared(self, title, slave_reference, cfg):
        ishared = {
            'slave_title':          title,
            'slave_reference':      slave_reference,
            'slap_software_type':   "enb",
            '_': json.dumps(cfg)
        }
        self.shared_instance_list.append(ishared)
        return ishared


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

    ienb.ishared('Cell 1a', '_CELL1_a', {
        'cell_type':    'lte',
        'rf_mode':      'tdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    38050,      # 2600 MHz
        'pci':          1,
        'cell_id':      '0x01',
        'ru':           RU1,        # RU definition embedded into CELL
    })

    ienb.ishared('Cell 1b', '_CELL1_b', {
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

    ienb.ishared('Cell 1c', '_CELL1_c', {
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

    ienb.ishared('Radio Unit 2a', '_RU2_a', RU2_a)
    ienb.ishared('Radio Unit 2b', '_RU2_b', RU2_b)

    ienb.ishared('Cell 2a', '_CELL2_a', {
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

    ienb.ishared('Cell 2b', '_CELL2_b', {
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

    ienb.ishared('Cell 3a', '_CELL3_a', {
        'cell_type':    'lte',
        'rf_mode':      'fdd',
        'bandwidth':    '5 MHz',
        'dl_earfcn':    3350,      # 2680 MHz (Band 7)
        'pci':          1,
        'cell_id':      '0x01',
        'ru':           RU,
    })

    ienb.ishared('Cell 3b', '_CELL3_b', {
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


def do_enb():
    ienb = Instance()
    iRU1_SDR_tLTE2_tNR(ienb)
    #iRU2_LOPCOMM_fLTE_fNR(ienb)
    #iRU3_SDR1_fLTE2(ienb)

    jshared_instance_list = json.dumps(ienb.shared_instance_list)
    json_params = """{
        "sib23_file": "sib2_3.asn",
        "slap_configuration": {
            "tap-name": "slaptap9",
            "slap-computer-partition-id": "slappart9",
            "configuration.default_lte_imsi": "001010123456789",
            "configuration.default_lte_k": "00112233445566778899aabbccddeeff",
            "configuration.default_lte_inactivity_timer": 10000,
            "configuration.default_nr_imsi": "001010123456789",
            "configuration.default_nr_k": "00112233445566778899aabbccddeeff",
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

    j2render('enb', json_params)


# ---- UE ----

def do_ue():
    iue = Instance()

    jshared_instance_list = json.dumps(iue.shared_instance_list)
    json_params = """{
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
        }
    }""" % locals()

    j2render('ue', json_params)


def main():
    do_enb()
    do_ue()


if __name__ == '__main__':
    main()
