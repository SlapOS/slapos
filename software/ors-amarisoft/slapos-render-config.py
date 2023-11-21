# Program slapos-render-config is handy during config/ templates development.
#
# It mimics the way config files are generated during the build but runs much
# faster compared to full `slapos node software` + `slapos node instance` runs.

import zc.buildout.buildout # XXX workaround for https://lab.nexedi.com/nexedi/slapos.recipe.template/merge_requests/9
from slapos.recipe.template import jinja2_template

import json


# j2render renders config/<cfg>.jinja2.cfg into config/<cfg>.cfg with provided json parameters.
def j2render(cfg, jcfg):
    ctx = json.loads(jcfg)
    textctx = ''
    for k, v in ctx.items():
        textctx += 'json %s %s\n' % (k, json.dumps(v))
    buildout = None # stub
    r = jinja2_template.Recipe(buildout, "recipe", {
      'extensions': 'jinja2.ext.do',
      'url': 'config/{}.jinja2.cfg'.format(cfg),
      'output': 'config/{}.cfg'.format(cfg),
      'context': textctx,
      })
    #print(r.context)

    # avoid dependency on zc.buildout.download and the need to use non-stub buildout section
    def _read(url, *args):
        with open(url, *args) as f:
            return f.read()
    r._read = _read

    with open('config/{}.cfg'.format(cfg), 'w+') as f:
      f.write(r._render().decode())


def do(cfg, slapparameter_dict):
    jslapparameter_dict = json.dumps(slapparameter_dict)
    json_params_empty = """{
        "rf_mode": 'fdd',
        "slap_configuration": {
        },
        "directory": {
        },
        "slapparameter_dict": %(jslapparameter_dict)s
    }"""
    json_params = """{
        "rf_mode": "tdd",
        "trx": "sdr",
        "bbu": "ors",
        "ru": "ors",
        "one_watt": "True",
        "earfcn": 646666,
        "nr_arfcn": 646666,
        "nr_band": 43,
        "tx_gain": 62,
        "rx_gain": 43,
        "sib23_file": "sib",
        "drb_file": "drb",
        "slap_configuration": {
            "tap-name": "slaptap9",
            "configuration.default_lte_bandwidth": "10 MHz",
            "configuration.default_lte_imsi": "001010123456789",
            "configuration.default_lte_k": "00112233445566778899aabbccddeeff",
            "configuration.default_lte_inactivity_timer": 10000,
            "configuration.default_nr_bandwidth": 40,
            "configuration.default_nr_imsi": "001010123456789",
            "configuration.default_nr_k": "00112233445566778899aabbccddeeff",
            "configuration.default_nr_ssb_pos_bitmap": "10000000",
            "configuration.default_n_antenna_dl": 2,
            "configuration.default_n_antenna_ul": 2,
            "configuration.default_nr_inactivity_timer": 10000,
            "configuration.com_ws_port": 9001,
            "configuration.com_addr": "127.0.1.2",
            "configuration.amf_addr": "127.0.1.100",
            "configuration.gtp_addr": "127.0.1.1"
        },
        "directory": {
            "log": "log",
            "etc": "etc",
            "var": "var"
        },
        "slapparameter_dict": %(jslapparameter_dict)s
    }"""

    j2render(cfg, json_params % locals())

do('gnb', {"tdd_ul_dl_config": "5ms 8UL 1DL 2/10 (maximum uplink)"})
