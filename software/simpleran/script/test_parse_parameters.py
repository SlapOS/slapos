import json
import time

class Object(object):
    pass

self = Object()

options = {
    'software': 'software-ors',
    'sbc-model': 'PD10ANS',
}
config = {
    "core_network_plmn": "46011",
    "pdn1": {
        "apn_list": [
            "Test"
        ],
        "qci": 9,
        "fixed_ips": True
    },
    "pdn2": {
        "apn_list": [
            "ims"
        ],
        "qci": 5,
        "fixed_ips": False,
        "volte": True
    }
}
sim_list = []
sim_list.append({
    "sim_algo": "xor",
    "plmn": "00101",
    "msin": "0123456789",
    "k": "00112233445566778899aabbccddeeff",
    "impi": "001010123456789@ims.mnc001.mcc001.3gppnetwork.org",
    "domain": "ims.mnc001.mcc001.3gppnetwork.org",
    "multi_sim": True,
    "force_ip": "172.21.128.8",
    "impu_list": [
        {
            "impu": "001010123456789"
        },
        {
            "impu": "tel:0600000000"
        },
        {
            "impu": "tel:600"
        }
    ]
})
slave_instance_list = []

for i, s in enumerate(sim_list):
	slave_instance_list.append({
		'_': json.dumps(s),
		'slap_software_type': 'core-network',
		'slave_reference': f'SOFTINST-{100000+i}',
		'slave_title': f'ORS100-SIM-{i}',
		'timestamp': time.time(),
	})


self.buildout = {
    'slap-configuration': {
		'instance-title': 'ors100-core-network',
        'slave-instance-list': slave_instance_list,
        'slap-software-type': 'core-network',
        'configuration': config,
        'ipv6-random': '1::',
    }
}


print(json.dumps(options, indent=4))

import netaddr
with open('script/parse-parameters.py', 'r') as f:
    exec(f.read())

print(json.dumps(options, indent=4))
