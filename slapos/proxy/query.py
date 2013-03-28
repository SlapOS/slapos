# -*- coding: utf-8 -*-
# vim: set et sts=4:

import collections
import ConfigParser
from optparse import OptionParser, Option
import sys

import lxml.etree
import sqlite3

from slapos.proxy.db_version import DB_VERSION



class Parser(OptionParser):
    """
    Parse all arguments.
    """
    def __init__(self, usage=None, version=None):
      """
      Initialize all options possibles.
      """
      OptionParser.__init__(self, usage=usage, version=version,
                            option_list=[
          Option("-u", "--database-uri",
                 type=str,
                 help="URI for sqlite database"),
          Option('--show-instances',
                 help="View instance information",
                 default=False,
                 action="store_true"),
          Option('--show-params',
                 help="View published parameters",
                 default=False,
                 action="store_true"),
          Option('--show-network',
                 help="View network information",
                 default=False,
                 action="store_true"),
          Option('--show-all',
                 help="View all information",
                 default=False,
                 action="store_true"),
      ])

    def check_args(self):
        """
        Check arguments
        """
        (options, args) = self.parse_args()
        if len(args) < 1:
            self.error("Incorrect number of arguments")

        return options, args[0]

class Config:
    def setConfig(self, option_dict, configuration_file_path):
        """
        Set options given by parameters.
        """
        # Set options parameters
        for option, value in option_dict.__dict__.items():
          setattr(self, option, value)

        # Load configuration file
        configuration_parser = ConfigParser.SafeConfigParser()
        configuration_parser.read(configuration_file_path)
        # Merges the arguments and configuration
        for section in ("slapproxy", "slapos"):
            configuration_dict = dict(configuration_parser.items(section))
            for key in configuration_dict:
                if not getattr(self, key, None):
                    setattr(self, key, configuration_dict[key])

        if not self.database_uri:
            raise ValueError('database-uri is required.')



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
    print '-+-'.join('-'*len(h) for h in hdr)

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




def run(config):
    conn = sqlite3.connect(config.database_uri)
    conn.row_factory = sqlite3.Row

    fn = []

    if config.show_all or config.show_instances:
        fn.append(print_tables)
    if config.show_all or config.show_params:
        fn.append(print_params)
    if config.show_all or config.show_network:
        fn.append(print_network)

    if fn:
        for f in fn:
            f(conn)
    else:
        print 'usage: %s [ --show-params | --show-network | --show-instances | --show-all ]' % sys.argv[0]



def main():
  "Run default configuration."
  usage = "usage: %s [options] CONFIGURATION_FILE" % sys.argv[0]

  try:
    # Parse arguments
    config = Config()
    config.setConfig(*Parser(usage=usage).check_args())

    run(config)
    return_code = 0
  except SystemExit, err:
    # Catch exception raise by optparse
    return_code = err

  sys.exit(return_code)



