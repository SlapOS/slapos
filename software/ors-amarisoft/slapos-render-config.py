# Program slapos-render-config is handy during config/ templates development.
#
# It mimics the way config files are generated during the build but runs much
# faster compared to full `slapos node software` + `slapos node instance` runs.

import zc.buildout.buildout # XXX workaround for https://lab.nexedi.com/nexedi/slapos.recipe.template/merge_requests/9
from slapos.recipe.template import jinja2_template

import json, os, glob


# j2render renders config/<src> into config/out/<out> with provided json parameters.
def j2render(src, out, jcfg):
    ctx = json.loads(jcfg)
    assert '_standalone' not in ctx
    ctx['_standalone'] = True
    textctx = ''
    for k, v in ctx.items():
        textctx += 'json %s %s\n' % (k, json.dumps(v))
    buildout = None # stub
    r = jinja2_template.Recipe(buildout, "recipe", {
      'extensions': 'jinja2.ext.do',
      'url': 'config/{}'.format(src),
      'output': 'config/out/{}'.format(out),
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

    with open('config/out/{}'.format(out), 'w+') as f:
      f.write(r._render().decode())


def do(src, out, rat, slapparameter_dict):
    assert rat in ('lte', 'nr')
    jdo_lte = json.dumps(rat == 'lte')
    jdo_nr  = json.dumps(rat == 'nr')
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
        "do_lte": %(jdo_lte)s,
        "do_nr": %(jdo_nr)s,
        "trx": "sdr",
        "bbu": "ors",
        "ru_type": "ors",
        "one_watt": "True",
        "earfcn": 36100,
        "nr_arfcn": 380000,
        "nr_band": 39,
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
            "configuration.mme_addr": "127.0.1.100",
            "configuration.gtp_addr": "127.0.1.1"
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

def do_enb():
    do('enb.jinja2.cfg', 'enb.cfg', 'lte', {"tdd_ul_dl_config": "[Configuration 6] 5ms 5UL 3DL (maximum uplink)"})
    do('enb.jinja2.cfg', 'gnb.cfg', 'nr',  {"tdd_ul_dl_config": "5ms 8UL 1DL 2/10 (maximum uplink)"})


def do_ue():
    do('ue.jinja2.cfg', 'ue-lte.cfg', 'lte', {'rue_addr': 'host1'})
    do('ue.jinja2.cfg',  'ue-nr.cfg',  'nr', {'rue_addr': 'host2'})


def main():
    os.makedirs('config/out', exist_ok=True)
    for f in glob.glob('config/out/*'):
        os.remove(f)
    do_enb()
    do_ue()


if __name__ == '__main__':
    main()
