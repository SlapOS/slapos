#!/usr/bin/env python

from ncclient import manager as nc
from lxml import etree
import json
import xmltodict

import sys, logging
from golang import func, defer, u


host = 'fe80::20a:ff:fe00:1020%slaptap9-1'
port = 830
user = 'oranuser'
password = 'oranpassword'

@func
def main():
    # log -> stderr
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

    m = nc.connect(host=host, port=port, username=user, password=password,
                   hostkey_verify=False)
    defer(m.close_session)
    #print(m)

    if 1:
        import time; time.sleep(2)
        return

    """
    for cap in m.server_capabilities:
        print('  ', cap)
    print()
    """

    #"""
    cfg = m.get_config(source='running')
    #xpprint(cfg.data)
    for ele in cfg.data:
        #print(ele.tag)
        if ele.tag == '{urn:ietf:params:xml:ns:yang:ietf-hardware}hardware':
            xpprint(ele)
    #"""

    """
    x = m.get()
    xpprint(x.data)
    """

    ok = m.create_subscription()
    print(ok)

    while 1:
        x = m.take_notification(timeout=5)
        if x is None:
            print('.', end='', flush=True)
            continue
        xpprint(x.notification_ele)




# xpprint pretty-prints XML element.
def xpprint(ele: etree.Element):
    #print(u(etree.tostring(ele, pretty_print=True)))
    _ = xmltodict.parse(etree.tostring(ele))
    jele = json.dumps(_)
    print(u(jele))


if __name__ == '__main__':
    main()
