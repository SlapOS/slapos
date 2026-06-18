import json, netaddr, math, socket, subprocess
from copy import deepcopy

"""
Inputs:

- lan-ipv4           : LAN IPv4
- sbc-model          : Single Board Computer Model
- software           : current software (e.g.: software-ors)
- slap-configuration : slap-configuration section from self.buildout
- publish            : Optionnal, connection parameters to publish

Outputs:

- slap-configuration : modified slap-configuration
- publish            : connection parameters to publish
- slapparameter-dict : slap-configuration.configuration
- shared-list        : slap-configuration.slave-instance-list
- sim-list           : Core Network only, list of SIM Cards
- dns-list           : Core Network only, list of DNS entries

"""

NR_TDD_CONFIG_MAP = {
    "DDDDDDDSUU (5ms,   7DL/2UL), S-slot=6DL:4GP:4UL, default"                      : 0,
    "DDDSUUDDDD (5ms,   7DL/2UL), S-slot=6DL:4GP:4UL, same ratios as default"       : 1,
    "DDDSUUUUDD (5ms,   5DL/4UL), S-slot=6DL:4GP:4UL, balanced downlink and uplink" : 2,
    "DDDSUUUUUU (5ms,   3DL/6UL), S-slot=2DL:2GP:10UL, high uplink"                 : 3,
    "DDSUUUUUUU (5ms,   2DL/7UL), S-slot=6DL:4GP:4UL, EXPERIMENTAL very high uplink": 4,
    "DSUUUUUUUU (5ms,   1DL/8UL), S-slot=10DL:2GP:2UL, EXPERIMENTAL maximum uplink" : 5,
    "DDDSU      (2.5ms, 3DL/1UL), S-slot=10DL:2GP:2UL, reduced latency"             : 6,
}
LTE_TDD_CONFIG_MAP = {
    "[Configuration 0] DSUUUDSUUU (5ms,  2DL/6UL), S-slot=10DL:2GP:2UL, maximum uplink"              : 0,
    "[Configuration 1] DSUUDDSUUD (5ms,  4DL/4UL), S-slot=10DL:2GP:2UL, balanced downlink and uplink": 1,
    "[Configuration 2] DSUDDDSUDD (5ms,  6DL/2UL), S-slot=10DL:2GP:2UL, default"                     : 2,
    "[Configuration 3] DSUUUDDDDD (10ms, 6DL/3UL), S-slot=10DL:2GP:2UL"                              : 3,
    "[Configuration 4] DSUUDDDDDD (10ms, 7DL/2UL), S-slot=10DL:2GP:2UL, high downlink"               : 4,
    "[Configuration 5] DSUDDDDDDD (10ms, 8DL/1UL), S-slot=10DL:2GP:2UL, maximum downlink"            : 5,
    "[Configuration 6] DSUUUDSUUD (5ms,  3DL/5UL), S-slot=10DL:2GP:2UL, high uplink"                 : 6,
}

def ors_radio(config, publish, shared_list):
    """eNB / gNB / UE - ORS Specific"""
    from xlte import nrarfcn
    from xlte import earfcn

    with open(options.get('json-ors-defaults'), 'r') as f:
        DEFAULTS = json.load(f)

    publish_sections = ['nodeb', 'cell', 'hardware', 'radio', 'id', 'power']
    for s in publish_sections:
        publish.setdefault(s, {})
    for s in ['cell1', 'cell2', 'nodeb', 'management']:
        config.setdefault(s, {})
    config.update(config['nodeb'])
    config.update(config['management'])
    del config['nodeb']
    del config['management']

    # Load rf-info from parameters (for E2E testing)
    if 'rf-info' in config:
        rf_info = json.loads(config['rf-info'])
    else:
        # Load rf-info.json file if existing
        try:
            rf_info_f = open('/etc/rf-info.json', 'r')
            rf_info = json.load(rf_info_f)
        except FileNotFoundError:
            rf_info = {}

    # Call get-sdr-info script to detect hardware
    def get_sdr_info(channel, opt):
        cmd = f"sudo -n {options['sdr-dir']}/get-sdr-info -{opt}"
        if channel == 1:
            cmd += f' -c{channel}'
        return subprocess.check_output(cmd.split(' ')).decode()

    # Detect SDR Hardware
    max_antenna = 0
    config['sdr100'] = False
    sdr_map = rf_info.setdefault('sdr_map', {})
    for channel in [0, 1]:
        sdr_info = sdr_map.setdefault(str(channel), {})
        if not sdr_info:
            for c in 'bmstv':
                prop = {'v': 'version', 't': 'tdd', 'b': 'band', 's': 'serial', 'm': 'model'}[c]
                try:
                    sdr_info[prop] = get_sdr_info(channel, c)
                except Exception:
                    pass
            if not sdr_info.get('model', ''):
                del sdr_map[str(channel)]
                continue
        max_antenna += 2
        sdr_info['version'] = float(sdr_info['version'])
        if sdr_info['model'] in ['ORS', 'ORSDUO']:
            sdr_info['power'] = '1W' if sdr_info['version'] >= 4 else '0.5W'
        elif sdr_info['model'] == 'ORSMAX':
            sdr_info['power'] = '10W'
        elif sdr_info['model'] == 'SDR100':
            config['sdr100'] = True
            sdr_info['power'] = '15mW'

    rf_info.setdefault('max_antenna', max_antenna)
    rf_info.setdefault('flavour', 'ORS')

    # Render ORS model for connection parameters
    sdr_list = list(sdr_map.values())
    if len(sdr_list) == 0:
        rf_info['flavour'] = None
        publish['hardware']['ors-version'] = 'No SDR hardware detected'
    else:
        if rf_info['flavour'] == 'ORSBRUTE':
            power = '20W'
            flavour = 'ORS Brute'
        else:
            if sdr_list[0]['model'] == 'ORSMAX':
                flavour = 'ORS Max'
            elif rf_info['flavour'] == 'BBU':
                flavour = 'BBU'
            elif len(sdr_map) > 1:
                flavour = 'ORS Duo'
            else:
                flavour = 'ORS Classic'
            if sdr_list[0]['power'] != sdr_list[-1]['power']:
                power = '+'.join([sdr['power'] for sdr in sdr_list])
            else:
                power = 'x'.join([str(rf_info['max_antenna']), sdr_list[0]['power']])
        if sdr_list[0]['tdd'] != sdr_list[-1]['tdd']:
            tdd = 'TDD+FDD'
            tdd = '+'.join([sdr['tdd'] for sdr in sdr_list])
        else:
            tdd = sdr_list[0]['tdd']
        band = '+'.join([sdr['band'] for sdr in sdr_list])
        publish['hardware']['ors-version'] = f'{flavour} {tdd} {band} {power}'
        config['cell1']['model'] = sdr_list[0]['band']
        if len(sdr_list) >= 2:
            config['cell2']['model'] = sdr_list[1]['band']

    for c in ['cell1', 'cell2']:
        if 'enable_cell' in config[c]:
            if config[c]['enable_cell'] == 'Enable eNB':
                config[c]['enable_cell'] = True
                config[c]['cell_type'] = 'eNB'
            elif config[c]['enable_cell'] == 'Enable gNB':
                config[c]['enable_cell'] = True
                config[c]['cell_type'] = 'gNB'
            elif config[c]['enable_cell'] == 'Enable NB IOT':
                config[c]['enable_cell'] = True
                config[c]['cell_type'] = 'NB'
            else:
                config[c]['enable_cell'] = False
        # UE
        if sr_type == 'ue':
            config[c] = config['cell']
            config.update(config['ue'])
            if 'dl_nr_arfcn' in config['cell']:
                config[c]['enable_cell'] = True
                config[c]['cell_type'] = 'gNB'
            else:
                config[c]['enable_cell'] = True
                config[c]['cell_type'] = 'eNB'

    # For ORS Classic, disable cell2
    if 'enable_cell' not in config['cell2']:
        config['cell2'].update(config['cell1'])
        config['cell2']['enable_cell'] = False
    # Disable cell if it has not been detected on the device
    for cell in ['cell1', 'cell2']:
        if 'model' not in config[cell]:
            config[cell]['enable_cell'] = False
            continue
        model = config[cell]['model']
        defaults = DEFAULTS[model]
        # Band specific defaults
        for param in 'rf_mode bandwidth nr_bandwidth bandwidth ssb_pos_bitmap'.split(' '):
            if param in defaults:
                config[cell].setdefault(param, defaults[param])

    # dBm and Gain conversion
    # Measurements were made in TDD, the power measured is thus 3.5/5
    #       below the real emitted power during the emission (because in TDD mode,
    #       we emit 3.5ms over a 5ms period).
    # Account for measurements done in TDD instead of FDD
    TDD_RATIO = 1.5490196
    def dbm_to_gain(tx_power, x):

        if not tx_power['coeff']:
            return None
        x -= TDD_RATIO
        a, b, c = tx_power['coeff']
        dbm = lambda x: a * x**2 + b * x + c
        power_min, power_max = dbm(tx_power['min']), dbm(tx_power['max'])

        # Assume TX gain is linear outside the tx gain values from interpolation
        if x <= power_min:
            return tx_power['min'] - (power_min - x)
        elif x >= power_max:
            return tx_power['max'] + (x - power_max)
        return (2 * (x - c)) / (math.sqrt(b**2 - 4 * a * (c - x)) + b)
    def gain_to_dbm(tx_power, x):
        if not tx_power['coeff']:
            return None
        a, b, c = tx_power['coeff']

        # Assume TX gain is linear outside the tx gain values from interpolation
        if x <= tx_power['min']:
            power = a * tx_power['min']**2 + b * tx_power['min'] + c - (tx_power['min'] - x)
        elif x >= tx_power['max']:
            power = a * tx_power['max']**2 + b * tx_power['max'] + c + (x - tx_power['max'])
        else:
            power = a * x**2 + b * x + c

        return power + TDD_RATIO

    # TX Power Offset is dB difference added by amplifiers
    def get_tx_power_offset(frequency, power_tx_gain_90):
        # https://tech-academy.amarisoft.com/trx_sdr.doc#TX-power
        # SDR50 power at tx_gain=90 depending on frequency
        amarisoft_power_map = {
            500:    3.0,
            1000: 3.0,
            1500: -1.0,
            2000: -2.0,
            2500: -2.5,
            3000: -4.5,
            3500: -4.5,
            4000: -5.5,
            4500: -9.0,
            5000: -14.5,
            5500: -18.0,
            6000: -18.0,
            9999: -18.0,
        }
        for freq in amarisoft_power_map:
            if frequency <= freq:
                amarisoft_power = amarisoft_power_map[freq]
                break
        # Experiments show we need to still add 9, we need to measure again RF Power
        return 9 + power_tx_gain_90 - amarisoft_power

    # NodeB Radio ID's
    def publish_hex(h):
        return f'{h} ({int(h, 16)})'
    sn = 0
    try:
        hostname = socket.gethostname()
        sn = int(''.join(filter(lambda x:x.isdigit(), hostname)))
    except (IndexError, ValueError):
        pass
    config.setdefault('enb_id', '0x{:05X}'.format( sn                    % 2**20))
    config.setdefault('gnb_id', '0x{:05X}'.format((sn + 2**19) % 2**20))
    publish['hardware']['serial-number'] = hostname.upper()
    publish['id']['gnb-id'] = publish_hex(config['gnb_id'])
    publish['id']['enb-id'] = publish_hex(config['enb_id'])

    # RF parameters (frequency, band, arfcn...)
    def configure_rf_parameters(i):

        c = f'cell{i+1}'
        sdr_info = sdr_list[i]

        if not config[c]['enable_cell']:
            return

        if config[c]['cell_type'] in ['eNB', 'NB']:
            rat = 'lte'
            lte, nr = True, False
        elif config[c]['cell_type'] == 'gNB':
            rat = 'nr'
            lte, nr = False, True
        model = sdr_info['band']
        defaults = DEFAULTS[model]

        # Use ARFCN or frequency depending on what is in input parameters
        band = config[c].get(rat + '_band', defaults[f'{rat}_band'])
        dl_arfcn_name = f"dl_{'e' if lte else 'nr_'}arfcn"
        ul_arfcn_name = f"ul_{'e' if lte else 'nr_'}arfcn"
        if dl_arfcn_name in config[c]:
            dl_arfcn = config[c][dl_arfcn_name]
            if lte:
                dl_frequency = earfcn.frequency(dl_arfcn)
                band         = earfcn.band(dl_arfcn)[0].band
            else:
                dl_frequency = nrarfcn.frequency(dl_arfcn)
        else:
            dl_frequency = config[c].get('dl_frequency', defaults[f'{rat}_frequency'])
            if rat == 'lte':
                dl_arfcn = earfcn.earfcn(dl_frequency, band)
            else:
                dl_arfcn = nrarfcn.nrarfcn(dl_frequency, nearby=True)
        if nr:
            if 'ssb_nr_arfcn' not in config[c]:
                for j in range(1, 11):
                    try:
                        _arfcn = dl_arfcn + (j // 2) * ((j % 2) * 2 - 1)
                        config[c]['ssb_nr_arfcn'], _ = nrarfcn.dl2ssb(_arfcn, band)
                    except KeyError as e:
                        continue
                    dl_arfcn = _arfcn
                    dl_frequency = nrarfcn.frequency(dl_arfcn)
                    break
            ul_arfcn = nrarfcn.dl2ul(dl_arfcn, band)
            ul_frequency = nrarfcn.frequency(ul_arfcn)
        else:
            ul_arfcn = earfcn.dl2ul(dl_arfcn)
            ul_frequency = earfcn.frequency(ul_arfcn)

        config[c][f'{rat}_band'] = band
        config[c][dl_arfcn_name] = dl_arfcn
        config[c][ul_arfcn_name] = ul_arfcn
        config[c]['dl_frequency'] = dl_frequency
        config[c]['ul_frequency'] = ul_frequency

        if config[c]['cell_type'] in ['eNB', 'gNB']:
            if rat == 'nr':
                config[c].setdefault('nr_bandwidth_ul', config[c]['nr_bandwidth'])
                config[c]['nr_bandwidth']    = float(config[c]['nr_bandwidth'   ].removesuffix(' MHz'))
                config[c]['nr_bandwidth_ul'] = float(config[c]['nr_bandwidth_ul'].removesuffix(' MHz'))
            else:
                config[c].setdefault('bandwidth_ul', config[c]['bandwidth'])
                config[c]['bandwidth']    = float(config[c]['bandwidth'   ].removesuffix(' MHz'))
                config[c]['bandwidth_ul'] = float(config[c]['bandwidth_ul'].removesuffix(' MHz'))

        # Bandwidth
        if config[c]['cell_type'] == 'gNB':
            if config[c]['nr_bandwidth_ul'] != config[c]['nr_bandwidth']:
                if config[c].get('subcarrier_spacing', 15 if config[c]['rf_mode'] == 'fdd' else 30) == 15:
                    n_rb_map = {
                        5 : 25,
                        10: 52,
                        15: 79,
                        20: 106,
                        25: 133,
                        30: 160,
                        35: 188,
                        40: 216,
                        45: 242,
                        50: 270,
                    }
                else:
                    n_rb_map = {
                        5 : 11,
                        10: 24,
                        15: 38,
                        20: 51,
                        25: 65,
                        30: 78,
                        35: 92,
                        40: 106,
                        45: 119,
                        50: 133,
                    }
                config[c]['n_rb_ul'] = n_rb_map[config[c]['nr_bandwidth_ul']]
                config[c]['n_rb_dl'] = n_rb_map[config[c]['nr_bandwidth']]
        elif config[c]['cell_type'] == 'eNB':
            if config[c]['bandwidth_ul'] != config[c]['bandwidth']:
                n_rb_map = {
                    1.4 : 6,
                    3: 15,
                    5: 25,
                    10: 50,
                    15: 75,
                    20: 100,
                }
                config[c]['n_rb_ul'] = n_rb_map[config[c]['bandwidth_ul']]
                config[c]['n_rb_dl'] = n_rb_map[config[c]['bandwidth']]

        publish['hardware'].setdefault('sdr-serial-number', {})
        publish['hardware']['sbc-model'] = options['sbc-model']
        publish['hardware']['sdr-serial-number'][c] = sdr_info['serial']

        publish['radio'].setdefault('dl-frequency', {})[c] = f'{dl_frequency} MHz'
        publish['radio'].setdefault('ul-frequency', {})[c] = f'{ul_frequency} MHz'
        publish['radio'].setdefault('band', {})[c] = f"{'b' if lte else 'n'}{band}"
        publish['radio'].setdefault('rf-mode', {})[c] = config[c]['rf_mode']
        if config[c]['cell_type'] == 'gNB':
            publish['radio'].setdefault('dl-nr-arfcn', {})[c] = dl_arfcn
            publish['radio'].setdefault('ul-nr-arfcn', {})[c] = ul_arfcn
            publish['radio'].setdefault('ssb-nr-arfcn', {})[c] = config[c]['ssb_nr_arfcn']
            publish['radio'].setdefault('bandwidth', {})[c] = f"{config[c]['nr_bandwidth']} MHz"
            if sr_type in ['enb', 'gnb', 'enb-gnb']:
                publish['radio'].setdefault('ssb-pos-bitmap', {})[c] = config[c]['ssb_pos_bitmap']
        elif config[c]['cell_type'] in ['eNB', 'NB']:
            publish['radio'].setdefault('dl-earfcn', {})[c] = dl_arfcn
            publish['radio'].setdefault('ul-earfcn', {})[c] = ul_arfcn
            if config[c]['cell_type'] == 'eNB':
                publish['radio'].setdefault('bandwidth', {})[c] = f"{config[c]['bandwidth']} MHz"

        # TX Gain, TX Power Offset, Range
        def round_float(f):
            return round(float(f) * 1000) / 1000
        tx_power_params = defaults['tx_power'][sdr_info['version'] >= 4]
        #       Compute TX Gain and TX Power dBm
        if 'tx_gain' in config[c]:
            tx_gain      = round_float(config[c]['tx_gain'])
            tx_power_dbm = round_float(gain_to_dbm(tx_power_params, tx_gain))
        else:
            tx_power_dbm = round_float(config[c]['tx_power_dbm'])
            tx_gain      = round_float(dbm_to_gain(tx_power_params, tx_power_dbm))

        #       Prepare published TX Power
        if tx_gain == None:
            tx_gain  = 0
            tx_power = 'Radio board unknown, please set tx_gain manually'
        elif tx_power_dbm == None:
            tx_power = 'Radio board unknown, cannot predict output power'
        else:
            tx_power_mw = 10 ** ( tx_power_dbm / 10 )
            if tx_power_mw < 0.01:
                tx_power_watt = '{:0.2f} µW'.format(tx_power_mw * 1000)
            else:
                tx_power_watt = '{:0.2f} mW'.format(tx_power_mw)
            tx_power = f'{tx_power_dbm} dBm, {tx_power_watt}'

        #       Compute TX Power offset
        if rf_info['flavour'] == 'ORSBRUTE':
            tx_power_offset = DEFAULTS['ORSBRUTE']['tx_power_offset']
        if sdr_info['model'] == 'ORSMAX':
            tx_power_offset = DEFAULTS['ORSMAX']['tx_power_offset']
        else:
            tx_power_offset = round_float(
                get_tx_power_offset(dl_frequency, gain_to_dbm(tx_power_params, 90))
            )

        config[c].setdefault('tx_power_offset', tx_power_offset)
        config[c]['tx_gain'] = tx_gain
        config[c]['range'] = defaults['range']
        publish['hardware'].setdefault('range', {})[c] = defaults['range']
        publish['power'].setdefault('tx-power', {})[c] = tx_power
        publish['power'].setdefault('tx-gain', {})[c] = f'{tx_gain} dB'
        publish['power'].setdefault('rx-gain', {})[c] = f"{config[c]['rx_gain']} dB"

        # Radio IDs
        if sr_type in ['enb', 'gnb', 'enb-gnb']:
            config[c].setdefault('pci', (sn + i * 252 * (nr+1)) % (504 * (nr+1)))
            config[c].setdefault('root_sequence_index', (sn + i * 79) % 138)
            config[c].setdefault('cell_id', '0x{:02X}'.format((sn + i * 2**7) % 2**8))
            def to_int(x):
                try:
                    return int(x, 16 if x.startswith('0x') else 10)
                except ValueError:
                    return 0
            global_id = lambda x,y,n: '0x{:07X}'.format(to_int(x) * 2**n + to_int(y))
            publish['id'].setdefault('physical-cell-id', {})[c]    = config[c]['pci']
            publish['id'].setdefault('root-sequence-index', {})[c] = config[c]['root_sequence_index']
            publish['id'].setdefault('cell-id', {})[c]             = publish_hex(config[c]['cell_id'])

            publish['id'].setdefault('handover-json-export', {})
            if config[c]['cell_type'] == 'eNB':
                publish['id'].setdefault('eutra-cell-id', {})
                eutra_cell_id = global_id(config['enb_id'], config[c]['cell_id'], 8)
                publish['id']['eutra-cell-id'][c] = publish_hex(eutra_cell_id)
                publish['cell'].setdefault('tac', {})[c] = config[c]['tac']
                publish['id']['handover-json-export'][c] = json.dumps({
                    'name': hostname,
                    'e_cell_id': global_id(config['enb_id'], config[c]['cell_id'], 8),
                    'dl_earfcn': dl_arfcn,
                    'pci': config[c]['pci'],
                    'tac': config[c]['tac'],
                    'plmn': config['plmn_list'][0]['plmn'],
                    })
            elif config[c]['cell_type'] == 'gNB':
                publish['id'].setdefault('nr-cell-id',      {})
                cid_len = 36 - config['gnb_id_bits']
                nr_cell_id = global_id(config['gnb_id'], config[c]['cell_id'], cid_len)
                publish['id']['nr-cell-id'][c] = publish_hex(nr_cell_id)
                publish['id']['handover-json-export'][c] = json.dumps({
                    'name': hostname,
                    'nr_cell_id': global_id(config['enb_id'], config[c]['cell_id'], 8),
                    'gnb_id_bits': config['gnb_id_bits'],
                    'dl_nr_arfcn': dl_arfcn,
                    'nr_band': band,
                    'ssb_nr_arfcn': config[c]['ssb_nr_arfcn'],
                    'ul_nr_arfcn': ul_arfcn,
                    'pci': config[c]['pci'],
                    'tac': config['plmn_list_5g'][0]['tac'],
                    'plmn': config['plmn_list_5g'][0]['plmn'],
                    })

            if config[c]['cell_type'] in ['eNB', 'gNB']:
                publish['radio'].setdefault('root-sequence-index', {})[c] = config[c]['root_sequence_index']
                publish['radio'].setdefault('tdd-ul-dl-config',      {})[c] = config[c]['tdd_ul_dl_config']

    def configure_cpu():
        if options['sbc-model'] != 'PD10ANS':
            return
        if config['cell1']['enable_cell'] and config['cell2']['enable_cell']:
            return
        if config['cell1']['enable_cell']:
            c = 'cell1'
        else:
            c = 'cell2'
        if config[c]['performance_mode'] == 'Maximum Uplink':
            config[c]['nb_threads_ul'] = 3
            config[c]['nb_threads_dl'] = 1
            return
        elif config[c]['performance_mode'] == 'Balanced':
            config[c]['nb_threads_ul'] = 2
            config[c]['nb_threads_dl'] = 2
            return
        elif config[c]['performance_mode'] == 'Maximum Downlink':
            config[c]['nb_threads_ul'] = 1
            config[c]['nb_threads_dl'] = 3
            return
        # Define number of UL threads
        if config[c]['cell_type'] == 'gNB':
            if config[c]['rf_mode'] == 'tdd':
                tdd_config = config[c]['tdd_ul_dl_config']
                if type(tdd_config) is dict:
                    p1 = tdd_config['pattern1']
                    p2 = tdd_config.get('pattern2')
                    if p2:
                        nb_ul_slot  = (p1['ul_slots'] + p1['ul_symbols']/14) * 5 / (p1['period'] + p2['period'])
                        nb_ul_slot += (p2['ul_slots'] + p2['ul_symbols']/14) * 5 / (p1['period'] + p2['period'])
                        nb_dl_slot  = (p1['dl_slots'] + p1['dl_symbols']/14) * 5 / (p1['period'] + p2['period'])
                        nb_dl_slot += (p2['dl_slots'] + p2['dl_symbols']/14) * 5 / (p1['period'] + p2['period'])
                    else:
                        nb_ul_slot = (p1['ul_slots'] + p1['ul_symbols']/14) * p1['period'] / 5
                        nb_dl_slot = (p1['dl_slots'] + p1['dl_symbols']/14) * p1['period'] / 5
                else:
                    nr_tdd_config = NR_TDD_CONFIG_MAP[tdd_config]
                    nb_ul_slot = {
                        0: 2 + 4/14,
                        1: 2 + 4/14,
                        2: 4 + 4/14,
                        3: 6 + 10/14,
                        4: 7 + 4/14,
                        5: 8 + 2/14,
                        6: 2 + 2/14,
                    }[nr_tdd_config]
                    nb_dl_slot = {
                        0: 7 + 6/14,
                        1: 7 + 6/14,
                        2: 5 + 6/14,
                        3: 3 + 2/14,
                        4: 2 + 6/14,
                        5: 1 + 10/14,
                        6: 6 + 10/14,
                    }[nr_tdd_config]
            elif config[c]['rf_mode'] == 'fdd':
                nb_ul_slot = 10
                nb_dl_slot = 10
            bandwidth_dl = config[c]['nr_bandwidth']
            bandwidth_ul = config[c]['nr_bandwidth_ul']
        elif config[c]['cell_type'] == 'eNB':
            if config[c]['rf_mode'] == 'tdd':
                tdd_config = config[c]['tdd_ul_dl_config']
                lte_tdd_config = LTE_TDD_CONFIG_MAP[tdd_config]
                nb_ul_slot = {
                    0: 6 + 2 * 2/14,
                    1: 4 + 2 * 2/14,
                    2: 2 + 2 * 2/14,
                    3: 3 + 2/14,
                    4: 2 + 2/14,
                    5: 1 + 2/14,
                    6: 5 + 2 * 2/14,
                }[lte_tdd_config]
                nb_dl_slot = {
                    0: 2 + 2 * 10/14,
                    1: 4 + 2 * 10/14,
                    2: 6 + 2 * 10/14,
                    3: 6 + 10/14,
                    4: 7 + 10/14,
                    5: 8 + 10/14,
                    6: 3 + 2 * 10/14,
                }[lte_tdd_config]
            elif config[c]['rf_mode'] == 'fdd':
                nb_ul_slot = 10
                nb_dl_slot = 10
            bandwidth_dl = config[c]['bandwidth']
            bandwidth_ul = config[c]['bandwidth_ul']
        else:
            return
        n_dl_layer = config['n_antenna_dl']
        n_ul_layer = config['n_antenna_ul']
        downlink_amount = nb_dl_slot * bandwidth_dl * n_dl_layer
        uplink_amount   = nb_ul_slot * bandwidth_ul * n_ul_layer
        if downlink_amount <= 800:
            config[c]['nb_threads_ul'] = 3
            config[c]['nb_threads_dl'] = 1
            return
        if uplink_amount <= 80:
            config[c]['nb_threads_ul'] = 1
            config[c]['nb_threads_dl'] = 3
            return
        if uplink_amount > 300 or (n_ul_layer >= 2 and uplink_amount > 150):
            publish['nodeb']['performance-warning'] = 'Warning: you might need to reduce the downlink / uplink bandwidth or number of antennas to avoid perfomance issues, your current settings exceed expected capacities of this SBC model.'

    if len(sdr_list) >= 1:
        configure_rf_parameters(0)
    if len(sdr_list) >= 2:
        configure_rf_parameters(1)

    configure_cpu()

    # ENB / GNB MODE
    if sr_type in ['enb', 'gnb', 'enb-gnb']:
        handover_id = lambda v: v.get('e_cell_id', v.get('nr_cell_id', 'UNKNOWN'))
        # AMF and PLMN List
        ncell_list   = config.get('ncell_list', [])
        plmn_list    = config.get('plmn_list', [])
        plmn_list_5g = config.get('plmn_list_5g', [])
        # Add default names
        for i, ncell in enumerate(ncell_list):
            ncell.setdefault('name', f'NeighbourCell{i}')
            if 'dl_earfcn' in ncell:
                ncell.setdefault('cell_type', 'lte')
                ncell.setdefault('cell_kind', 'enb_peer')
            else:
                ncell.setdefault('cell_type', 'nr')
                ncell.setdefault('cell_kind', 'enb_peer')
        config.setdefault('gtp_addr_list', [config['gtp_addr']])
        if max(config['n_antenna_ul'], config['n_antenna_dl']) > 2:
            n_cell = config['cell1']['enable_cell'] + config['cell2']['enable_cell']
            if n_cell == 0:
                sdr_dev_list = []
            elif n_cell == 1:
                sdr_dev_list = [0, 1]
            elif n_cell == 2:
                raise AssertionError('Both cells are enabled but antenna count is higher than 2')
        else:
            sdr_dev_list = [0] if config['cell1']['enable_cell'] else []
            sdr_dev_list += [1] if config['cell2']['enable_cell'] else []
        # make real ru/cell/peer/... shared instances to be rejected in ORS mode
        for shared in shared_list:
            shared_params = json.loads(shared['_'])
            if 'ru_type' in shared_params or 'cell_type' in shared_params:
                shared.update({'_': json.dumps({'REJECT': 1})})
        lte_cell = 0
        nr_cell = 0
        nb_cell = 0
        for i in range(2):
            cell = f'cell{i + 1}'
            if config[cell]['enable_cell']:
                ru_params = {
                    'ru_type':          'sdr',
                    'ru_link_type': 'sdr',
                    'sdr_dev_list': [i] if max(config['n_antenna_ul'], config['n_antenna_dl']) <= 2 else [0, 1],
                    'n_antenna_dl': config['n_antenna_dl'],
                    'n_antenna_ul': config['n_antenna_ul'],
                    'txrx_active':  'ACTIVE',
                }
                for k in 'tx_gain rx_gain tx_power_offset nb_threads_ul nb_threads_dl'.split(' '):
                    if k in config[cell]:
                        ru_params[k] = config[cell][k]
                shared_list.append({
                    'slave_title': f'SDR{i}',
                    'slave_reference':  False,
                    '_': json.dumps(ru_params),
                })
                if config[cell]['cell_type'] == 'eNB':
                    lte_cell += 1
                    cell_params = {
                        'cell_type':                        'lte',
                    }
                elif config[cell]['cell_type'] == 'gNB':
                    nr_cell += 1
                    config[cell]['bandwidth'] = config[cell]['nr_bandwidth']
                    cell_params = {
                        'cell_type':                        'nr',
                    }
                else:
                    nb_cell += 1
                    cell_params = {
                        'cell_type':                        'nb',
                    }
                config[cell]['inactivity_timer'] = config['inactivity_timer']
                for k in config[cell]:
                    if k != 'cell_type':
                        cell_params[k] = config[cell][k]
                for k in 'nr_bandwidth tx_gain rx_gain tx_power_offset tx_power_dbm model'.split(' '):
                    cell_params.pop(k, '')

                cell_params.update({
                    'cell_kind':    'enb',
                    'ru': { 'ru_type': 'ru_ref',
                            'ru_ref' : f'SDR{i}'}
                })
                shared_list.append({
                    'slave_title'    : f'CELL{i}',
                    'slave_reference': False,
                    '_': json.dumps(cell_params),
                })
        for i, ncell in enumerate(config['ncell_list']):
            shared_list.append({
                'slave_title'    : f"PEERCELL{ncell.get('name', i)}",
                'slave_reference': False,
                '_': json.dumps(ncell),
            })

        # Neighbour Cell List
        publish['cell']['neighbour-cell-list'] = ', '.join(
                ['{} ({})'.format(ncell['name'], handover_id(ncell)) for ncell in ncell_list])
        # PLMN Cell List
        if lte_cell or nb_cell:
            publish['cell']['4g-plmn-list'] = ', '.join([x['plmn'] for x in plmn_list])
        if nr_cell:
            publish['cell']['5g-plmn-list'] = ', '.join(
                [f"{x['plmn']} (TAC: {x['tac']})" for x in plmn_list_5g])
        # AMF and PLMN List
        if not (lte_cell or nb_cell):
            config.pop('mme_list', '')
        if not nr_cell:
            config.pop('amf_list', '')
        mme_list = config.get('mme_list', [])
        amf_list = config.get('amf_list', [])
        # Add default names
        for i, mme in enumerate(mme_list):
            mme.setdefault('name', f'MME{i}')
        publish['nodeb']['mme-list'] = ', '.join(
                ['{} ({})'.format(mme['name'], mme['mme_addr']) for mme in mme_list])
        for i, amf in enumerate(amf_list):
            amf.setdefault('name', f'AMF{i}')
        publish['nodeb']['amf-list'] = ', '.join(
                ['{} ({})'.format(amf['name'], amf['amf_addr']) for amf in amf_list])
        for i, peer in enumerate(config['x2_peers']):
            shared_list.append({
                'slave_title'    : f"X2_PEER{peer.get('name', i)}",
                'slave_reference': False,
                '_': json.dumps({
                    'peer_type': 'lte',
                    'x2_addr'  : peer['x2_addr'],
                })
            })
        for i, peer in enumerate(config['xn_peers']):
            shared_list.append({
                'slave_title'    : f"X2_PEER{peer.get('name', i)}",
                'slave_reference': False,
                '_': json.dumps({
                    'peer_type': 'nr',
                    'xn_addr'  : peer['xn_addr'],
                })
            })

    if sr_type == 'gnb' and options['software'] == 'software-ors':
        # backward compatibility: if ORS is running in gnb mode, and gnb_* parameters
        #       are present, replace their generic enb_* counterparts with gnb_* ones
        if 'gnb_stats_fetch_period' in config:
            config['enb_stats_fetch_period'] = config['gnb_stats_fetch_period']
        if 'gnb_drb_stats_enabled' in config:
            config['enb_drb_stats_enabled'] =  config['gnb_drb_stats_enabled']

    # UE MODE
    if sr_type == 'ue':
        shared_list.append({
                'slave_title':          'SDR',
                'slave_reference':  False,
                '_': json.dumps({
                    'ru_type':      'sdr',
                    'ru_link_type': 'sdr',
                    'sdr_dev_list': [0] if config['cell_number'] == 'First Cell' else [1],
                    'n_antenna_dl': config['n_antenna_dl'],
                    'n_antenna_ul': config['n_antenna_ul'],
                    'tx_gain':      config['cell1']['tx_gain'],
                    'rx_gain':      config['cell1']['rx_gain'],
                    'txrx_active':  'ACTIVE'    if (not config['disable_sdr'])  else    'INACTIVE',
                })})
        config['sim'].setdefault('imsi', config['sim']['plmn'] + config['sim']['msin'])
        if config[cell]['cell_type'] == 'eNB':
            shared_list.append({
                    'slave_title':          'CELL1',
                    'slave_reference':  False,
                    '_': json.dumps({
                        'cell_type':    'lte',
                        'dl_earfcn':    config['cell1']['dl_earfcn'],
                        'bandwidth':    float(config['cell1']['bandwidth'].removesuffix(' MHz')),
                        'cell_kind':    'ue',
                        'rf_mode':      config['cell1']['rf_mode'],
                        'ru': { 'ru_type':  'ru_ref',
                                'ru_ref':       'SDR' }
                    })})
            shared_list.append({
                    'slave_title':          'UESIM1',
                    'slave_reference':  False,
                    '_': json.dumps({
                        'ue_type':  'lte',
                        'imsi':         config['sim']['imsi'],
                        'k':                config['sim']['k'],
                        'opc':          config['sim']['opc'],
                        'sqn':          config['sim']['sqn'],
                        'sim_algo': config['sim']['sim_algo'],
                    })})
        else:
            shared_list.append({
                    'slave_title':          'CELL1',
                    'slave_reference':  False,
                    '_': json.dumps({
                        'cell_type':    'nr',
                        'dl_nr_arfcn':  config['cell1']['dl_nr_arfcn'],
                        'nr_band':      config['cell1']['nr_band'],
                        'ssb_nr_arfcn': config['cell1']['ssb_nr_arfcn'],
                        'bandwidth':    float(config['cell1']['nr_bandwidth']),
                        'cell_kind':    'ue',
                        'rf_mode':      config['cell1']['rf_mode'],
                        'ru': { 'ru_type':  'ru_ref',
                                'ru_ref':       'SDR' }
                    })})
            shared_list.append({
                    'slave_title':          'UESIM1',
                    'slave_reference':  False,
                    '_': json.dumps({
                        'ue_type':  'nr',
                        'imsi':     config['sim']['imsi'],
                        'k':        config['sim']['k'],
                        'opc':      config['sim']['opc'],
                        'sqn':      config['sim']['sqn'],
                        'sim_algo': config['sim']['sim_algo'],
                    })})
        for shared in shared_list:
            shared_params = json.loads(shared['_'])
            if 'imsi' in shared_params:
                shared_params.update({'ue_type': 'lte'})

    def publish_merge_cell(d):
        if type(d) is dict:
            if 'cell1' in d or 'cell2' in d:
                if config['cell1']['enable_cell']:
                    d.setdefault('cell1', 'Not applicable')
                if config['cell2']['enable_cell']:
                    d.setdefault('cell2', 'Not applicable')
                return ' / '.join([str(d[k]) for k in sorted(d)])
            for k in d:
                d[k] = publish_merge_cell(d[k])
        return d
    publish = publish_merge_cell(publish)

    # Add descriptions
    if 'tx-power' in publish['power']:
        publish['power']['tx-power'] += ' (Maximum average power if all ressource blocks are used)'

def core_network(config, publish, shared_list):

    publish_sections = ['network', 'core', 'pdn', 'sim']
    for s in publish_sections:
        publish.setdefault(s, {})

    config.setdefault('gtp_addr_list', ['Localhost address'])

    tun_ipv4_addr    = slap_configuration.get('tun-ipv4-addr', '172.17.0.1')
    tun_ipv6_addr    = slap_configuration.get('tun-ipv6-addr', '2001:db8::1')
    tun_ipv4_network = slap_configuration.get('tun-ipv4-network', '172.17.0.0/17')
    tun_ipv6_network = slap_configuration.get('tun-ipv6-network', '2001:db8::/55')
    tun_ipv4_start   = int(netaddr.IPAddress(tun_ipv4_addr))
    tun_ipv6_start   = int(netaddr.IPAddress(tun_ipv6_addr))
    tun_ipv4_end     = netaddr.IPNetwork(tun_ipv4_network).last
    tun_ipv6_end     = netaddr.IPNetwork(tun_ipv6_network).last

    config.update({
        'tun_name'           : slap_configuration.get('tun-name', 'slaptun0'              ),
        'internet_ipv4'      : str(netaddr.IPAddress( tun_ipv4_start                          )),
        'internet_ipv4_start': str(netaddr.IPAddress( tun_ipv4_start + 1                      )),
        'internet_ipv4_end'  : str(netaddr.IPAddress((tun_ipv4_start + tun_ipv4_end) // 2 - 2 )),
        'internet_ipv6_start': str(netaddr.IPAddress( tun_ipv6_start + 1                      )),
        'internet_ipv6_end'  : str(netaddr.IPAddress((tun_ipv6_start + tun_ipv6_end) // 2 - 1 )),
        'ims_ipv4_start'     : str(netaddr.IPAddress((tun_ipv4_start + tun_ipv4_end) // 2 + 2 )),
        'ims_ipv4_end'       : str(netaddr.IPAddress( tun_ipv4_end   - 1                      )),
        'ims_ipv4'           : str(netaddr.IPAddress((tun_ipv4_start + tun_ipv4_end) // 2 + 1 )),
        'ims_ipv6'           : str(netaddr.IPAddress((tun_ipv6_start + tun_ipv6_end) // 2     )),
        'ims_ipv6_start'     : str(netaddr.IPAddress((tun_ipv6_start + tun_ipv6_end) // 2     )),
        'ims_ipv6_end'       : str(netaddr.IPAddress( tun_ipv6_end   - 1                      )),
    })

    # Sort shared list by IMSI
    def load_param(shared):
        shared['_'] = json.loads(shared['_'])
        return shared
    def dump_param(shared):
        shared['_'] = json.dumps(shared['_'])
        return shared

    def parse_sim_param(shared):
        p = shared['_']
        p.setdefault('imsi', p.get('plmn', '') + p.get('msin', ''))
        p.setdefault('msin', p.get('imsi', '')[5:])
        p.setdefault('plmn', p.get('imsi', '')[:5])
        if len(p['imsi']) != 15:
            p['error'] = 'MSIN has wrong length'
        p.setdefault('plmn', '00101')
        p.setdefault('mcc', p['plmn'][:3])
        if len(p['plmn']) == 5:
            p.setdefault('mnc', f"0{p['plmn'][3:]}")
        elif len(p['plmn']) == 6:
            p.setdefault('mnc', p['plmn'][3:])
        else:
            p['error'] = 'PLMN has wrong length'
        return shared

    def check_dup(shared_list):
        imsi_map = {}
        for s in shared_list:
            imsi_map.setdefault(s['_']['imsi'], []).append(s['slave_title'])
        for s in shared_list:
            instance_list = imsi_map[s['_']['imsi']]
            if len(instance_list) > 1:
                s['_']['error'] = 'Duplicate IMSI error. The following SIM Card Instances have the same IMSI: {}. Please keep only one.'.format(', '.join(instance_list))
        return shared_list

    def disable_faulty_sim(shared):
        if 'error' in shared['_']:
            shared['_']['disable_sim'] = 'Disable SIM'
        return shared

    shared_list = map(load_param, shared_list)
    shared_list = map(parse_sim_param, shared_list)
    shared_list = sorted(shared_list, key=lambda x: x['_'].get('imsi',''))
    shared_list = check_dup(shared_list)
    shared_list = map(disable_faulty_sim, shared_list)
    shared_list = map(dump_param, shared_list)
    shared_list = list(shared_list)

    # Defaults for global core network parameters.
    # TODO automatically load mme defaults from JSON schema
    mme_defaults = {
        'testing': False,
        'iperf3': 0,
        'core_network_plmn': '00101',
        'eps_5gs_interworking': 'With N26',
        'network_name': 'RAPIDSPACE',
        'network_short_name': 'RAPIDSPACE',
        'mme_com_ws_port':  9002,
        'mme_com_addr': '127.0.1.3',
        'ims_com_ws_port':  9004,
        'ims_com_addr': '127.0.1.5',
        'com_unsecure':     False,
        'websocket_url_ipv6': False,
        'ims_addr': '127.0.0.1',
        'ims_bind': '127.0.0.2',
        'qci':  9,
        'pdn_list': [
            {'name': 'internet'},
            {'name': 'default'},
            {'name': 'sos'}
        ]
    }
    for k,v in mme_defaults.items():
        config.setdefault(k, v)
    if config['websocket_url_ipv6']:
        ipv6 = slap_configuration['ipv6-random']
        config['mme_com_addr'] = ipv6
        config['mme_com_url' ] = f"[{ipv6}]:{config['mme_com_ws_port']}"
        config['ims_com_addr'] = ipv6
        config['ims_com_url' ] = f"[{ipv6}]:{config['ims_com_ws_port']}"
        config['com_unsecure'] = True
    else:
        config['mme_com_url'] = f"{config['mme_com_addr']}:{config['mme_com_ws_port']}"
        config['ims_com_url'] = f"{config['ims_com_addr']}:{config['ims_com_ws_port']}"
    config.setdefault('fixed_ips', False)

    sim_list = []
    dns_list = []
    for shared in shared_list:
        p = json.loads(shared['_'])
        p.setdefault('slave_reference', shared['slave_reference'])
        if p.get('subdomain', '') != '':
            dns_list.append(p)
        elif p.get('k', '') != '':
            sim_list.append(p)
            impi = f"{p['imsi']}@ims.mnc{p['mnc']}.mcc{p['mcc']}.3gppnetwork.org"
            p.setdefault('impi', impi)
            p.setdefault('impu', p['imsi'])
            p['impu'] = f'"{p["impu"]}"'
            if p.get('impu_list', ''):
                impu_list = []
                for x in p['impu_list']:
                    impu_list.append(x['impu'])
                impu_str = '", "'.join(impu_list)
                p['impu'] = f'["{impu_str}"]'

    def valid_ip(network, ip):
        try:
            netaddr_ip = netaddr.IPAddress(ip)
            return netaddr_ip in network
        except netaddr.core.AddrFormatError:
            return False

    network = netaddr.IPNetwork(slap_configuration.get('tun-ipv4-network', ''))
    # if we don't have enough IPv4 addresses in the network, don't force it
    # should we make a promise fail ?
    if len(sim_list) + 2 > network.size:
        for s in sim_list:
            s['ip'] = 'Too many SIM for the IPv4 network'
    else:
        # calculate the IP addresses of each SIM
        ip_list = []
        first_addr = netaddr.IPAddress(network.first)
        force_ip_list = []
        for s in sim_list:
            ip = s.get('force_ip', None)
            if ip and valid_ip(network, ip):
                s['ip'] = ip
                force_ip_list.append(ip)
        i = 2
        for s in sorted(sim_list, key=lambda x: x['imsi']):
            if 'ip' in s:
                continue
            ip = str(first_addr + i)
            while ip in force_ip_list:
                i += 1
                ip = str(first_addr + i)
            s['ip'] = ip
            i += 1

    publish['core']['plmn']               = config['core_network_plmn']
    publish['core']['sip-bind-ip']        = config['ims_ipv4']
    publish['core']['network-name']       = config['network_name']
    publish['core']['network-short-name'] = config['network_short_name']

    publish['pdn']['gateway-ipv4']    = slap_configuration['tun-ipv4-addr']
    publish['pdn']['ipv4-subnetwork'] = slap_configuration['tun-ipv4-network']
    publish['pdn']['pdn-list'] = ', '.join([pdn['name'] for pdn in config['pdn_list']])

    return sim_list, dns_list

def gtp_addr(gtp_localhost_addr):
    gtp_addr_list = []
    for gtp_addr in config['gtp_addr_list']:
        if gtp_addr == 'Automatic':
            for a in (config.get('mme_list', []) + config.get('amf_list', [])):
                addr = a.get('mme_addr', a.get('amf_addr', ''))
                if '[' in addr:
                    addr = addr.split('[', 1)[1].rsplit(']', 1)[0]
                elif '.' in addr and ':' in addr:
                    addr = addr.split(':', 1)[0]

                ip = netaddr.IPAddress(addr)
                if ip.is_loopback():
                    gtp_addr_list.append(gtp_localhost_addr)
                elif ':' in addr:
                    gtp_addr_list.append(slap_configuration['ipv6-random'])
                else:
                    r = subprocess.check_output(['ip', '-json', 'route', 'get', addr])
                    gtp_addr_list.append(json.loads(r)[0]['prefsrc'])
        elif gtp_addr == 'IPv4 LAN address':
            gtp_addr_list.append(options['lan-ipv4'])
        elif gtp_addr == 'IPv6 Re6st address':
            gtp_addr_list.append(slap_configuration['ipv6-random'])
        elif gtp_addr == 'Localhost address':
            gtp_addr_list.append(gtp_localhost_addr)
        else:
            gtp_addr_list.append(gtp_addr)
    config['gtp_addr_list'] = gtp_addr_list or [gtp_localhost_addr]

def test_model(config, publish, shared_list):
    for i, cell in enumerate(['cell1', 'cell2']):
        config.setdefault(cell, {})
        config[cell].setdefault('enable_cell', False)
        if not config[cell]['enable_cell']:
            continue
        # Default parameters (TODO: use slap-configuration:jsonschemas recipe)
        config[cell].setdefault('file', 'LTE Test Mode 31  - 20 MHz  - FDD')
        config[cell].setdefault('enable_cell', True)
        sp = list(filter(lambda x: x, config[cell]['file'].split(' ')))
        config[cell]['file'] = {
         'LTE Test Mode 31  - 10 MHz    - FDD':              'LTE-31-10MHzBP_SR1536-FDD-ADJUSTED.bin',
         'LTE Test Mode 31  - 10 MHz    - TDD':              'LTE-31-10MHzBP_SR1536-TDD-ADJUSTED.bin',
         'LTE Test Mode 31  - 1.4 MHz - TDD':                'LTE-31-1p4MHzBP_SR1p92-TDD-ADJUSTED.bin',
         'LTE Test Mode 31  - 20 MHz    - FDD':              'LTE-31-20MHzBP_SR3072-FDD-ADJUSTED.bin',
         'LTE Test Mode 31  - 3 MHz     - TDD':              'LTE-31-3MHzBP_SR3p84-TDD-ADJUSTED.bin',
         'LTE Test Mode 31  - 5 MHz     - TDD':              'LTE-31-5MHzBP_SR7p68-TDD-ADJUSTED.bin',
         'LTE Test Mode 32  - 10 MHz    - TDD':              'LTE-32-10MHzBP_SR1536-TDD-ADJUSTED.bin',
         'LTE Test Mode 32  - 20 MHz    - TDD':              'LTE-32-20MHzBP_SR3072-TDD-ADJUSTED.bin',
         'LTE Test Mode 33  - 10 MHz    - TDD':              'LTE-33-10MHzBP_SR1536-TDD-ADJUSTED.bin',
         'LTE Test Mode 33  - 20 MHz    - TDD':              'LTE-33-20MHzBP_SR3072-TDD-ADJUSTED.bin',
         'LTE Test Mode 31  - 20 MHz    - TDD':              'LTE-TM_31-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 11    - 20 MHz    - TDD':          'NR-FR1-TM11-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 11    - 5 MHz     - FDD':          'NR-FR1-TM11-5MHz_SR7680000-FDD-ADJUSTED.bin',
         'NR    Test Mode 12    - 20 MHz    - TDD':          'NR-FR1-TM12-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 2     - 20 MHz    - TDD':          'NR-FR1-TM2-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 2a    - 20 MHz    - TDD':          'NR-FR1-TM2a-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 2b    - 20 MHz    - TDD':          'NR-FR1-TM2b-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 31    - 100 MHz - FDD':            'NR-FR1-TM31-100MHz_SR122880000_SCS30kHz-FDD-ADJUSTED.bin',
         'NR    Test Mode 31    - 20 MHz    - FDD':          'NR-FR1-TM31-20MHz_SR30720000-FDD-ADJUSTED.bin',
         'NR    Test Mode 31    - 20 MHz    - TDD':          'NR-FR1-TM31-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 31    - 40 MHz    - TDD':          'NR-FR1-TM31-40MHz_SR61440000-TDD-ADJUSTED.bin',
         'NR    Test Mode 31    - 5 MHz     - FDD':          'NR-FR1-TM31-5MHz_SR7680000-FDD-ADJUSTED.bin',
         'NR    Test Mode 31a - 20 MHz  - FDD':              'NR-FR1-TM_31a-20MHzBP_SC30kHz_SR30p72-FDD-ADJUSTED.bin',
         'NR    Test Mode 31a - 20 MHz  - FDD - SCS 15 kHz': 'NR-FR1-TM31a-20MHz_SR30720000_SCS15kHz-FDD-ADJUSTED.bin',
         'NR    Test Mode 31a - 20 MHz  - TDD':              'NR-FR1-TM31a-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 31a - 5 MHz       - FDD':          'NR-FR1-TM31a-5MHz_SR7680000-FDD-ADJUSTED.bin',
         'NR    Test Mode 31b - 20 MHz  - TDD':              'NR-FR1-TM31b-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 32    - 20 MHz    - TDD':          'NR-FR1-TM32-20MHz_SR30720000-TDD-ADJUSTED.bin',
         'NR    Test Mode 33    - 20 MHz    - TDD':          'NR-FR1-TM33-20MHz_SR30720000-TDD-ADJUSTED.bin',
        }[config[cell]['file']]
        bandwidth = int(sp[5])
        config[cell]['rf_mode'] = sp[8].lower()
        config[cell]['rat'] = sp[0].lower()
        config[cell]['test_mode'] = sp[3]
        config[cell]['scs'] = 30 if len(sp) < 10 else sp[11]
        config[cell]['rate'] = {
            1.4: 1920000,
            3  : 3840000,
            5  : 7680000,
            10 : 15360000,
            20 : 30720000,
            40 : 61440000,
            100: 122880000,
        }[bandwidth]
        config[cell]['bandwidth'] = f'{bandwidth} MHz'
        config[cell]['rate'] = f"{config[cell]['rate'] / 10**6} MHz"
        config[cell]['dl_frequency'] *= 10**6

def flatten(d):
    if type(d) is not dict:
        return [[d]]
    l = []
    for k in d:
        s = flatten(d[k])
        for x in s:
            l.append([k] + x)
    return l

def publish_naming(l):
    n = 0
    for i in range(len(l) - 1):
        l[i] = l[i].upper()
        n += len(l[i])
    return '.'.join(l)

def delete_empty(d):
    out = {}
    for k in d:
        if type(d[k]) is dict and d[k] != {}:
            out[k] = delete_empty(d[k])
        elif type(d[k]) is not dict:
            out[k] = d[k]
    return out

slap_configuration = deepcopy(self.buildout['slap-configuration'])
publish            = deepcopy(options.get('publish', {}))
shared_list        = deepcopy(slap_configuration['slave-instance-list'])
config             = slap_configuration['configuration']
sr_type            = slap_configuration['slap-software-type']

if config.get('testing', False):
    for k,v in {
        'ipv4': "{'192.0.2.1'}",
        'ipv6': "{'2001:db8::1'}",
        'tun-ipv4-addr': '192.0.2.1',
        'tun-ipv4-gateway': '',
        'tun-ipv4-netmask': '255.255.128.0',
        'tun-ipv4-network': '192.0.2.1/255.255.128.0',
        'tun-ipv6-addr': '2001:db8::1',
        'tun-ipv6-netmask': 'ffff:ffff:ffff:fe00::',
        'tun-ipv6-network': '2001:db8::1/55',
        'tun-name': 'slaptun1',
        }.items():
        slap_configuration.setdefault(k, v)

if sr_type == 'test-model':
    test_model(config, publish, shared_list)

if options['software'].startswith('software-ors') and sr_type in ['enb', 'gnb', 'ue', 'enb-gnb']:
    ors_radio(config, publish, shared_list)

if sr_type == 'core-network':
    gtp_localhost_addr = '127.0.1.100'
    sim_list, dns_list = core_network(config, publish, shared_list)
elif sr_type in ['enb-gnb', 'enb', 'gnb']:
    gtp_localhost_addr = '127.0.1.1'
    config.setdefault('gtp_addr', 'Automatic')
    config.setdefault('gtp_addr_list', [config['gtp_addr']])

if sr_type in ['core-network', 'enb-gnb', 'enb', 'gnb']:
    gtp_addr(gtp_localhost_addr)

if sr_type == 'core-network':
    publish['core']['gtp-addr-list'] = ', '.join(config['gtp_addr_list'])
elif options['software'].startswith('software-ors') and sr_type in ['enb', 'gnb', 'enb-gnb']:
    publish['nodeb']['gtp-addr'] = config['gtp_addr_list'][0]

publish = delete_empty(publish)
publish = flatten(publish)
publish = {publish_naming(k[:-1]): k[-1] for k in publish}

for k,v in slap_configuration.items():
    if type(v) is set:
        slap_configuration[k] = list(slap_configuration[k])

slap_configuration.update({
    'configuration': config,
    'slave-instance-list': shared_list,
})
options['publish'] = publish
options['slap-configuration'] = slap_configuration
options['slapparameter-dict'] = config
options['shared-list'] = shared_list

if sr_type == 'core-network':
    options['sim-list'] = sim_list
    options['dns-list'] = dns_list
