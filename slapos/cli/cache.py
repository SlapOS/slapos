# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import ast
import hashlib
import json
import re
import requests
import sys

import prettytable

from slapos.grid import networkcache
from slapos.grid.distribution import distribution_tuple
from slapos.cli.config import ConfigCommand


class CacheLookupCommand(ConfigCommand):
    """
    perform a query to the networkcache
    You can provide either a complete URL to the software release,
    or a corresponding MD5 hash value.

    The command will report which OS distribution/version have a binary
    cache of the software release, and which ones are compatible
    with the OS you are currently running.
    """

    def get_parser(self, prog_name):
        ap = super(CacheLookupCommand, self).get_parser(prog_name)
        ap.add_argument('software_url',
                        help='Your software url or MD5 hash')
        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        cache_dir = configp.get('networkcache', 'download-binary-dir-url')
        do_lookup(self.app.log, cache_dir, args.software_url)


def looks_like_md5(s):
    """
    Return True if the parameter looks like an hashed value.
    Not 100% precise, but we're actually more interested in filtering out URLs and pathnames.
    """
    return re.match('[0-9a-f]{32}', s)


def do_lookup(logger, cache_dir, software_url):
    if looks_like_md5(software_url):
        md5 = software_url
    else:
        md5 = hashlib.md5(software_url).hexdigest()

    try:
        url = '%s/%s' % (cache_dir, md5)
        logger.debug('Connecting to %s', url)
        req = requests.get(url, timeout=5)
    except (requests.Timeout, requests.ConnectionError):
        logger.critical('Cannot connect to cache server at %s', url)
        sys.exit(10)

    if not req.ok:
        if req.status_code == 404:
            logger.critical('Object not in cache: %s', software_url)
        else:
            logger.critical('Error while looking object %s: %s', software_url, req.reason)
        sys.exit(10)

    entries = req.json()

    if not entries:
        logger.info('Object found in cache, but has no binary entries.')
        return

    ostable = sorted(ast.literal_eval(json.loads(entry[0])['os']) for entry in entries)

    pt = prettytable.PrettyTable(['distribution', 'version', 'id', 'compatible?'])

    linux_distribution = distribution_tuple()

    for os in ostable:
        compatible = 'yes' if networkcache.os_matches(os, linux_distribution) else 'no'
        pt.add_row([os[0], os[1], os[2], compatible])

    meta = json.loads(entries[0][0])
    logger.info('Software URL: %s', meta['software_url'])
    logger.info('MD5:          %s', md5)

    for line in pt.get_string(border=True, padding_width=0, vrules=prettytable.NONE).split('\n'):
        logger.info(line)
