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

import collections
import hashlib

import lxml.etree
import prettytable
import sqlite3

from slapos.cli.config import ConfigCommand
from slapos.proxy import ProxyConfig
from slapos.proxy.db_version import DB_VERSION
from slapos.util import sqlite_connect


class ProxyShowCommand(ConfigCommand):
    """
    display proxy instances and parameters
    """

    def get_parser(self, prog_name):
        ap = super(ProxyShowCommand, self).get_parser(prog_name)

        ap.add_argument('-u', '--database-uri',
                        help='URI for sqlite database')

        ap.add_argument('--computers',
                        help='view computer information',
                        action='store_true')

        ap.add_argument('--software',
                        help='view software releases',
                        action='store_true')

        ap.add_argument('--partitions',
                        help='view partitions',
                        action='store_true')

        ap.add_argument('--slaves',
                        help='view slave instances',
                        action='store_true')

        ap.add_argument('--params',
                        help='view published parameters',
                        action='store_true')

        ap.add_argument('--network',
                        help='view network settings',
                        action='store_true')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ProxyConfig(logger=self.app.log)
        conf.mergeConfig(args, configp)
        conf.setConfig()
        do_show(conf=conf)


tbl_partition = 'partition' + DB_VERSION


def coalesce(*seq):
    el = None
    for el in seq:
        if el is not None:
            return el
    return el


def log_table(logger, qry, tablename, skip=None):
    if skip is None:
        skip = set()

    columns = [c[0] for c in qry.description if c[0] not in skip]

    rows = []
    for row in qry.fetchall():
        rows.append([coalesce(row[col], '-') for col in columns])

    pt = prettytable.PrettyTable(columns)
    # https://code.google.com/p/prettytable/wiki/Tutorial

    for row in rows:
        pt.add_row(row)

    if rows:
        if skip:
            logger.info('table %s: skipping %s', tablename, ', '.join(skip))
        else:
            logger.info('table %s', tablename)
    else:
        logger.info('table %s: empty', tablename)
        return

    for line in pt.get_string(border=True, padding_width=0, vrules=prettytable.NONE).split('\n'):
        logger.info(line)


def log_params(logger, conn):
    cur = conn.cursor()

    qry = cur.execute("SELECT reference, partition_reference, software_type, connection_xml FROM %s" % tbl_partition)
    for row in qry.fetchall():
        if not row['connection_xml']:
            continue

        xml = str(row['connection_xml'])
        logger.info('%s: %s (type %s)', row['reference'], row['partition_reference'], row['software_type'])
        instance = lxml.etree.fromstring(xml)
        for parameter in list(instance):
            name = parameter.get('id')
            text = parameter.text
            if text and name in ('ssh-key', 'ssh-public-key'):
                text = text[:20] + '...' + text[-20:]
            logger.info('    %s = %s', name, text)


def log_computer_table(logger, conn):
    tbl_computer = 'computer' + DB_VERSION
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_computer)
    log_table(logger, qry, tbl_computer)


def log_software_table(logger, conn):
    tbl_software = 'software' + DB_VERSION
    cur = conn.cursor()
    qry = cur.execute("SELECT *, md5(url) as md5 FROM %s" % tbl_software)
    log_table(logger, qry, tbl_software)


def log_partition_table(logger, conn):
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s WHERE slap_state<>'free'" % tbl_partition)
    log_table(logger, qry, tbl_partition, skip=['xml', 'connection_xml', 'slave_instance_list'])


def log_slave_table(logger, conn):
    tbl_slave = 'slave' + DB_VERSION
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_slave)
    log_table(logger, qry, tbl_slave, skip=['connection_xml'])


def log_network(logger, conn):
    tbl_partition_network = 'partition_network' + DB_VERSION
    cur = conn.cursor()
    addr = collections.defaultdict(list)
    qry = cur.execute("""
                      SELECT * FROM %s
                       WHERE partition_reference NOT IN (
                                                SELECT reference
                                                  FROM %s
                                                 WHERE slap_state='free')
                        """ % (tbl_partition_network, tbl_partition))
    for row in qry:
        addr[row['partition_reference']].append(row['address'])

    for partition_reference in sorted(addr.keys()):
        addresses = addr[partition_reference]
        logger.info('%s: %s', partition_reference, ', '.join(addresses))


def do_show(conf):
    conf.logger.debug('Using database: %s', conf.database_uri)
    conn = sqlite_connect(conf.database_uri)
    conn.row_factory = sqlite3.Row

    conn.create_function('md5', 1, lambda s: hashlib.md5(s).hexdigest())

    call_table = [
        (conf.computers, log_computer_table),
        (conf.software, log_software_table),
        (conf.partitions, log_partition_table),
        (conf.slaves, log_slave_table),
        (conf.params, log_params),
        (conf.network, log_network)
    ]

    if not any(flag for flag, func in call_table):
        to_call = [func for flag, func in call_table]
    else:
        to_call = [func for flag, func in call_table if flag]

    for idx, func in enumerate(to_call):
        func(conf.logger, conn)
        if idx < len(to_call) - 1:
            conf.logger.info(' ')
