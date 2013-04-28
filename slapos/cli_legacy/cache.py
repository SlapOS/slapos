# -*- coding: utf-8 -*-

import argparse
import ConfigParser

from slapos.cache import do_lookup


def cache_lookup():
    ap = argparse.ArgumentParser()
    ap.add_argument("configuration_file", help="SlapOS configuration file")
    ap.add_argument("software_url", help="Your software url or MD5 hash")
    args = ap.parse_args()

    config = ConfigParser.SafeConfigParser()
    config.read(args.configuration_file)

    do_lookup(config, args.software_url)
