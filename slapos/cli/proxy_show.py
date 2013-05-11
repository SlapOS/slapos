# -*- coding: utf-8 -*-

import collections
import logging

from slapos.cli.config import ConfigCommand
from slapos.proxy import ProxyConfig

import lxml.etree
import sqlite3

from slapos.proxy.db_version import DB_VERSION


class ProxyShowCommand(ConfigCommand):
    """
    display proxy instances and parameters
    """

    log = logging.getLogger('proxy')

    def get_parser(self, prog_name):
        ap = super(ProxyShowCommand, self).get_parser(prog_name)

        ap.add_argument('-u', '--database-uri',
                        help='URI for sqlite database')

        ap.add_argument('--instances',
                        help='view instance information',
                        action='store_true')

        ap.add_argument('--params',
                        help='view published parameters',
                        action='store_true')

        ap.add_argument('--network',
                        help='view network information',
                        action='store_true')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ProxyConfig(logger=self.log)
        conf.mergeConfig(args, configp)
        conf.setConfig()
        do_show(conf=conf)


tbl_computer = 'computer' + DB_VERSION
tbl_software = 'software' + DB_VERSION
tbl_partition = 'partition' + DB_VERSION
tbl_partition_network = 'partition_network' + DB_VERSION
tbl_slave = 'slave' + DB_VERSION

null_str = u"-"


def print_table(qry, tablename, skip=None):
    if skip is None:
        skip = set()

    columns = [c[0] for c in qry.description if c[0] not in skip]
    rows = []
    for row in qry.fetchall():
        line = {}
        for col in columns:
            val = row[col]
            if val is None:
                val = null_str
            line[col] = val.strip()
        rows.append(line)

    max_width = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = row[col]
            max_width[col] = max(max_width[col], len(val) if val else 0)

    hdr = [col.center(max_width[col]) for col in columns]

    print

    if rows:
        print 'table %s:' % tablename,
    else:
        print 'table %s: empty' % tablename
        return

    if skip:
        print 'skipping %s' % ', '.join(skip)
    else:
        print

    print ' | '.join(hdr)
    print '-+-'.join('-' * len(h) for h in hdr)

    for row in rows:
        cells = [row[col].ljust(max_width[col]) for col in columns]
        print ' | '.join(cells)


def print_params(conn):
    cur = conn.cursor()

    print

    qry = cur.execute("SELECT reference, partition_reference, software_type, connection_xml FROM %s" % tbl_partition)
    for row in qry.fetchall():
        if not row['connection_xml']:
            continue

        xml = str(row['connection_xml'])
        print '%s: %s (type %s)' % (row['reference'], row['partition_reference'], row['software_type'])
        instance = lxml.etree.fromstring(xml)
        for parameter in list(instance):
            name = parameter.get('id')
            text = parameter.text
            if text and name in ('ssh-key', 'ssh-public-key'):
                text = text[:20] + '...' + text[-20:]
            print '    %s = %s' % (name, text)
        print


def print_computer_table(conn):
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_computer)
    print_table(qry, tbl_computer)


def print_software_table(conn):
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_software)
    print_table(qry, tbl_software)


def print_partition_table(conn):
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s WHERE slap_state<>'free'" % tbl_partition)
    print_table(qry, tbl_partition, skip=['xml', 'connection_xml', 'slave_instance_list'])


def print_slave_table(conn):
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_slave)
    print_table(qry, tbl_slave, skip=['connection_xml'])


def print_tables(conn):
    print_computer_table(conn)
    print_software_table(conn)
    print_partition_table(conn)
    print_slave_table(conn)


def print_network(conn):
    print
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
        print '%s: %s' % (partition_reference, ', '.join(addresses))


def do_show(conf):
    conn = sqlite3.connect(conf.database_uri)
    conn.row_factory = sqlite3.Row

    print_all = (not conf.instances and not conf.params and not conf.network)

    if print_all or conf.instances:
        print_tables(conn)
    if print_all or conf.params:
        print_params(conn)
    if print_all or conf.network:
        print_network(conn)
