# Program slapos-render-config is handy during config/ templates development.
#
# It mimics the way config files are generated during the build but runs much
# faster compared to full `slapos node software` + `slapos node instance` runs.

import zc.buildout.buildout # XXX workaround for https://lab.nexedi.com/nexedi/slapos.recipe.template/merge_requests/9
from slapos.recipe.template import jinja2_template

import json, copy, sys, os, pprint, shutil


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
    textctx += 'import json_module    json\n'
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


# ---- eNB ----

# ORS_eNB and ORS_gNB mimic what instance-ors-enb.jinja2.cfg does.
ORS_ru = {
    'ru_type':      'sdr',
    'ru_link_type': 'sdr',
    'sdr_dev':      0,
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
    for f in (ORS_enb,
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
            'ssb_nr_arfcn':     520090,
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

    # TODO render drb.cfg + sib.asn for all cells


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
