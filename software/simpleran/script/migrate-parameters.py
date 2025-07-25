#!/usr/bin/env python3

# Script to migrate raw XML input parameters of eNB/gNB software types from <1.0.427 to 1.0.427+

import json
import argparse

def convert_tdd(params):

<<<<<<< HEAD
params_json_raw = '{' + params_raw.split('{', 1)[1].rsplit('}', 1)[0] + '}'
params = json.loads(params_json_raw)
new_params = {}

def convert_tdd(old):
=======
    k = 'tdd_ul_dl_config'
    if k not in params:
        return
>>>>>>> 1dde7ff5c (simpleran: write migration script)

    conversion_table = {
        "5ms 2UL 7DL 4/6 (default)": \
          "DDDDDDDSUU (5ms,   7DL/2UL), S-slot=6DL:4GP:4UL,  default",
        "2.5ms 1UL 3DL 2/10": \
          "DDDSU      (2.5ms, 1UL/3DL), S-slot=10DL:2GP:2UL,  reduced latency)",
        "5ms 6UL 3DL 10/2 (high uplink)": \
          "DDDSUUUUUU (5ms,   6UL/3DL), S-slot=2DL:2GP:10UL, high uplink)",
        "5ms 7UL 2DL 4/6 (EXPERIMENTAL very high uplink)": \
          "DDSUUUUUUU (5ms,   7UL/2DL), S-slot=6DL:4GP:4UL,  EXPERIMENTAL very high uplink)",
        "5ms 8UL 1DL 2/10 (EXPERIMENTAL maximum uplink)": \
          "DSUUUUUUUU (5ms,   8UL/1DL), S-slot=10DL:2GP:2UL,  EXPERIMENTAL maximum uplink)",
        "[Configuration 2] 5ms 2UL 6DL (default)": \
          "[Configuration 2] DSUDDDSUDD (5ms,  6DL/2UL), S-slot=10DL:2GP:2UL, default",
        "[Configuration 6] 5ms 5UL 3DL (maximum uplink)": \
          "[Configuration 6] DSUUUDSUUD (5ms,  3DL/5UL), S-slot=10DL:2GP:2UL, high uplink",
    }
    good_values = [
        "DDDDDDDSUU (5ms,   7DL/2UL), S-slot=6DL:4GP:4UL,  default",
        "DDDSUUDDDD (5ms,   2UL/7DL), S-slot=6DL:4GP:4UL,  same ratios as default",
        "DDDSUUUUDD (5ms,   4UL/5DL), S-slot=6DL:4GP:4UL,  balanced downlink and uplink)",
        "DDDSUUUUUU (5ms,   6UL/3DL), S-slot=2DL:2GP:10UL, high uplink)",
        "DDSUUUUUUU (5ms,   7UL/2DL), S-slot=6DL:4GP:4UL,  EXPERIMENTAL very high uplink)",
        "DSUUUUUUUU (5ms,   8UL/1DL), S-slot=10DL:2GP:2UL,  EXPERIMENTAL maximum uplink)",
        "DDDSU      (2.5ms, 1UL/3DL), S-slot=10DL:2GP:2UL,  reduced latency)",
        "[Configuration 0] DSUUUDSUUU (5ms,  2DL/6UL), S-slot=10DL:2GP:2UL, maximum uplink",
        "[Configuration 1] DSUUDDSUUD (5ms,  4DL/4UL), S-slot=10DL:2GP:2UL, balanced downlink and uplink",
        "[Configuration 2] DSUDDDSUDD (5ms,  6DL/2UL), S-slot=10DL:2GP:2UL, default",
        "[Configuration 3] DSUUUDDDDD (10ms, 6DL/3UL), S-slot=10DL:2GP:2UL",
        "[Configuration 4] DSUUDDDDDD (10ms, 7DL/2UL), S-slot=10DL:2GP:2UL, high downlink",
        "[Configuration 5] DSUDDDDDDD (10ms, 8DL/1UL), S-slot=10DL:2GP:2UL, maximum downlink",
        "[Configuration 6] DSUUUDSUUD (5ms,  3DL/5UL), S-slot=10DL:2GP:2UL, high uplink",
    ]

    if old in good_values:
        return old
    elif old in conversion_table:
        return conversion_table[old]
    else:
        print("Unknown TDD UL DL parameter, exiting")
        exit(1)

<<<<<<< HEAD

if 'ors_duo_2nd_cell' in params:
    new_params['ors_cell2'] = params['ors_duo_2nd_cell']

ors_cell_params = [
    "tx_power_dbm",
    "tx_gain",
    "rx_gain",
    "nr_band",
    "dl_frequency",
    "dl_nr_arfcn",
    "ssb_nr_arfcn",
    "ssb_pos_bitmap",
    "nr_bandwidth",
    "tdd_ul_dl_config",
    "pci",
    "cell_id",
    "root_sequence_index",
    "tx_power_offset",
    "bandwidth",
    "lte_band",
    "dl_earfcn",
    "tac",
]
ors_enb_gnb_params = [
    "n_antenna_dl",
    "n_antenna_ul",
    "ors_duo_mode",
    "gps_sync",
    "amf_list",
    "plmn_list",
    "gnb_id",
    "gnb_id_bits",
    "ncell_list",
    "nr_nr_handover",
    "nr_eutra_handover",
    "xn_peers",
    "gtp_addr",
    "mbmsgw_addr",
    "handover_a1_rsrp",
    "handover_a1_hysteresis",
    "handover_a1_time_to_trigger",
    "handover_a2_rsrp",
    "handover_a2_hysteresis",
    "handover_a2_time_to_trigger",
    "handover_meas_gap_config",
    "inactivity_timer",
    "disable_sdr",
    "nssai",
    "enb_id",
    "mme_list",
    "eutra_eutra_handover",
    "eutra_nr_handover",
    "x2_peers",
]

ors_params = [
    "log_phy_debug",
    "enb_stats_fetch_period",
    "enb_drb_stats_enabled",
    "max_rx_sample_db",
    "min_rxtx_delay",
    "xlog_enabled",
    "xlog_forwarding_enabled",
    "wendelin_telecom_software_release_url",
    "xlog_fluentbit_forward_host",
    "xlog_fluentbit_forward_port",
    "xlog_fluentbit_forward_shared_key",
]


for param in params:
    if param == 'ors_duo_2nd_cell':
        continue
    if param in ['ors_cell1', 'ors_cell2', 'ors_enb_gnb', 'ors']:
        new_params.setdefault(param, {}).update(params[param])
    elif param in ors_cell_params:
        new_params.setdefault('ors_cell1',   {})[param] = params[param]
    elif param in ors_enb_gnb_params:
        new_params.setdefault('ors_enb_gnb', {})[param] = params[param]
    elif param in ors_params:
        new_params.setdefault('ors',         {})[param] = params[param]
    elif param == 'use_ipv4':
        continue
    else:
        print("Unknown parameter: {}, exiting".format(param))
        exit(1)

for p in ['ors_cell1', 'ors_cell2']:
    if p in new_params:
        if 'tdd_ul_dl_config' in new_params[p]:
            new_params[p]['tdd_ul_dl_config'] = convert_tdd(new_params[p]['tdd_ul_dl_config'])
=======
def convert_to_array(params):
    for k in [\
            'ncell_list',
            'mme_list',
            'amf_list',
            'xn_peers',
            'x2_peers',
            ]:
        if k in params:
            new = []
            for name in params[k]:
                new.append(params[k][name])
                new[-1]['name'] = name
            params[k] = new
    for k in [\
            'plmn_list',
            'impu_list',
            'pdn_list',
            'plmn_list_5g',
            'nssai',
            ]:
        if k in params:
            params[k] = list(params[k].values())
>>>>>>> 1dde7ff5c (simpleran: write migration script)

def convert_gtp(params):
    if 'gtp_addr' in params:
        params['_gtp_addr'] = params['gtp_addr']
        params.pop('gtp_addr')

def convert_ors_params(params, new_params):

    if 'ors_duo_2nd_cell' in params:
        new_params['ors_cell2'] = params['ors_duo_2nd_cell']
    
    ors_cell_params = [
        "tx_power_dbm",
        "tx_gain",
        "rx_gain",
        "nr_band",
        "dl_frequency",
        "dl_nr_arfcn",
        "ssb_nr_arfcn",
        "ssb_pos_bitmap",
        "nr_bandwidth",
        "tdd_ul_dl_config",
        "pci",
        "cell_id",
        "root_sequence_index",
        "tx_power_offset",
        "bandwidth",
        "lte_band",
        "dl_earfcn",
        "tac",
    ]
    ors_enb_gnb_params = [
        "n_antenna_dl",
        "n_antenna_ul",
        "ors_duo_mode",
        "gps_sync",
        "amf_list",
        "plmn_list",
        "gnb_id",
        "gnb_id_bits",
        "ncell_list",
        "nr_nr_handover",
        "nr_eutra_handover",
        "xn_peers",
        "gtp_addr",
        "gtp_addr_list",
        "mbmsgw_addr",
        "handover_a1_rsrp",
        "handover_a1_hysteresis",
        "handover_a1_time_to_trigger",
        "handover_a2_rsrp",
        "handover_a2_hysteresis",
        "handover_a2_time_to_trigger",
        "handover_meas_gap_config",
        "inactivity_timer",
        "disable_sdr",
        "nssai",
        "enb_id",
        "mme_list",
        "eutra_eutra_handover",
        "eutra_nr_handover",
        "x2_peers",
    ]
    
    ors_params = [
        "log_phy_debug",
        "enb_stats_fetch_period",
        "enb_drb_stats_enabled",
        "max_rx_sample_db",
        "min_rxtx_delay",
        "xlog_enabled",
        "xlog_forwarding_enabled",
        "wendelin_telecom_software_release_url",
        "xlog_fluentbit_forward_host",
        "xlog_fluentbit_forward_port",
        "xlog_fluentbit_forward_shared_key",
    ]
    
    for param in params:
        if param == 'ors_duo_2nd_cell':
            continue
        if param in ['ors_cell1', 'ors_cell2', 'ors_enb_gnb', 'ors']:
            new_params.setdefault(param, {}).update(params[param])
        elif param in ors_cell_params:
            new_params.setdefault('ors_cell1',   {})[param] = params[param]
        elif param in ors_enb_gnb_params:
            new_params.setdefault('ors_enb_gnb', {})[param] = params[param]
        elif param in ors_params:
            new_params.setdefault('ors',         {})[param] = params[param]
        elif param == 'use_ipv4':
            continue
        else:
            print("Unknown parameter: {}, exiting".format(param))
            exit(1)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--bbu', action='store_true')
    parser.add_argument('--core', action='store_true')
    args = parser.parse_args()

    print('Paste here the raw XML parameters to migrate:')
    params_raw = ""
    for i in range(10000):
        l = input()
        params_raw += l
        if '</instance>' in l:
            break
    
    params_json_raw = '{' + params_raw.split('{', 1)[1].rsplit('}', 1)[0] + '}'
    params = json.loads(params_json_raw)
    new_params = {}

    if not (args.bbu or args.core):
        convert_ors_params(params, new_params)
        for p in new_params:
            convert_tdd(new_params[p])
            convert_gtp(new_params[p])
            convert_to_array(new_params[p])
    else:
        convert_tdd(new_params)
        convert_gtp(new_params)
        convert_to_array(new_params)
    
    new_params_raw = """<?xml version="1.0" encoding="UTF-8"?>
    <instance>
        <parameter id="_">"""
    
    new_params_raw += json.dumps(new_params)
    
    new_params_raw += """</parameter>
    </instance>"""
    
    print("")
    print("Paste these parameters in raw XML parameter:")
    print("")
    print(new_params_raw)

if __name__ == '__main__':
    main()

