# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2016 Vifib SARL and Contributors.
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

import os
import argparse
import csv

from slapos.util import mkdir_p
from slapos.collect.db import Database

def skip_bootstrap(self):
  return

Database._bootstrap = skip_bootstrap

def parseArguments():
  """
  Parse arguments for monitor collector instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_folder',
                      help='Path of the folder where output files should be written.')
  parser.add_argument('--collector_db',
                      default='/srv/slapgrid/var/data-log/',
                      help='The path of slapos collect database is located.')

  return parser.parse_args()

def writeFile(name, folder, date_scope, rows):
  if os.path.exists(
      os.path.join(folder, "%s/dump_%s.csv" % (date_scope, name))):
    # File already exists, no reason to recreate it.
    return
  mkdir_p(os.path.join(folder, date_scope), 0o755)
  file_io = open(os.path.join(folder, "%s/dump_%s.csv" % (date_scope, name)), "w")
  csv_output = csv.writer(file_io)
  csv_output.writerows(rows)
  file_io.close()

def dump_table_into_csv(db, folder):
    db.connect()
    table_list = db.getTableList()
    # Save all dates first, as db.selector may switch the cursor
    date_list = [(date_scope, _) \
       for date_scope, _ in db.getDateScopeList(reported=1)]

    for date_scope, amount in date_list:
      for table in table_list:
        if os.path.exists(
            os.path.join(folder, "%s/dump_%s.csv" % (date_scope, table))):
          # File already exists, no reason to recreate it.
          continue
        writeFile(table, folder, date_scope, 
              db.select(table, date_scope))
    db.close()


if __name__ == "__main__":
  parser = parseArguments()
  if parser.output_folder is None:
    raise Exception("Invalid ouput folder: %s" % parser.output_folder)
  
  if parser.collector_db is None:
    raise Exception("Invalid collector database folder: %s" % parser.collector_db)
  
  
  if not os.path.exists(parser.output_folder) and \
          os.path.isdir(parser.output_folder):
    raise Exception("Invalid ouput folder: %s" % parser.output_folder)

  
  if not os.path.exists(parser.collector_db):
    print "Collector database not found..."

  dump_table_into_csv(Database(parser.collector_db), parser.output_folder)
