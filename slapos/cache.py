# -*- coding: utf-8 -*-

import ast
import hashlib
import json
import re
import sys
import urllib2

from slapos.grid import networkcache
from slapos.grid.distribution import patched_linux_distribution


def maybe_md5(s):
    return re.match('[0-9a-f]{32}', s)


def do_lookup(configp, software_url):
    cache_dir = configp.get('networkcache', 'download-binary-dir-url')

    if maybe_md5(software_url):
        md5 = software_url
    else:
        md5 = hashlib.md5(software_url).hexdigest()

    try:
        response = urllib2.urlopen('%s/%s' % (cache_dir, md5))
    except urllib2.HTTPError as e:
        if e.code == 404:
            print 'Object not in cache: %s' % software_url
        else:
            print 'Error during cache lookup: %s (%s)' % (e.code, e.reason)
        sys.exit(10)

    entries = json.loads(response.read())

    linux_distribution = patched_linux_distribution()

    header_printed = False

    ostable = []
    for entry in entries:
        meta = json.loads(entry[0])
        os = ast.literal_eval(meta['os'])
        if not header_printed:
            print 'Software URL: %s' % meta['software_url']
            print 'MD5:          %s' % md5
            print '-------------'
            print 'Available for: '
            print 'distribution     |   version    |       id       | compatible?'
            print '-----------------+--------------+----------------+-------------'
            header_printed = True
        ostable.append(os)
    ostable.sort()

    for os in ostable:
        compatible = 'yes' if networkcache.os_matches(os, linux_distribution) else 'no'
        print '%-16s | %12s | %s | %s' % (os[0], os[1], os[2].center(14), compatible)
