# -*- coding: utf-8 -*-

import collections
import hashlib
import logging

import lxml.etree
import prettytable
import sqlite3

from slapos.cli.config import ConfigCommand
from slapos.proxy import ProxyConfig
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
        conf = ProxyConfig(logger=self.log)
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


def print_table(qry, tablename, skip=None):
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
        print 'table %s:' % tablename,
        if skip:
            print 'skipping %s' % ', '.join(skip)
        else:
            print
    else:
        print 'table %s: empty' % tablename
        return

    print pt.get_string(border=True, padding_width=0, vrules=prettytable.NONE)


def print_params(conn):
    cur = conn.cursor()

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


def print_computer_table(conn):
    tbl_computer = 'computer' + DB_VERSION
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_computer)
    print_table(qry, tbl_computer)


def print_software_table(conn):
    tbl_software = 'software' + DB_VERSION
    cur = conn.cursor()
    qry = cur.execute("SELECT *, md5(url) as md5 FROM %s" % tbl_software)
    print_table(qry, tbl_software)


def print_partition_table(conn):
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s WHERE slap_state<>'free'" % tbl_partition)
    print_table(qry, tbl_partition, skip=['xml', 'connection_xml', 'slave_instance_list'])


def print_slave_table(conn):
    tbl_slave = 'slave' + DB_VERSION
    cur = conn.cursor()
    qry = cur.execute("SELECT * FROM %s" % tbl_slave)
    print_table(qry, tbl_slave, skip=['connection_xml'])


def print_network(conn):
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
        print '%s: %s' % (partition_reference, ', '.join(addresses))


def do_show(conf):
    conn = sqlite3.connect(conf.database_uri)
    conn.row_factory = sqlite3.Row

    conn.create_function('md5', 1, lambda s: hashlib.md5(s).hexdigest())

    print_all = not any([
        conf.computers,
        conf.software,
        conf.partitions,
        conf.slaves,
        conf.params,
        conf.network,
    ])

    if print_all or conf.computers:
        print_computer_table(conn)
        print
    if print_all or conf.software:
        print_software_table(conn)
        print
    if print_all or conf.partitions:
        print_partition_table(conn)
        print
    if print_all or conf.slaves:
        print_slave_table(conn)
        print
    if print_all or conf.params:
        print_params(conn)
        print
    if print_all or conf.network:
        print_network(conn)
        print
