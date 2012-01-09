##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import os
import sqlite3
import uuid

from slapos.recipe.librecipe import GenericBaseRecipe

class UIDDatabase(object):

  def __init__(self, database_path, name):
    if not os.path.exists(database_path):
      open(database_path, 'w').close() # Just a touch
    self.database_path = database_path
    self.name = name

  def __enter__(self):
    self.database = sqlite3.connect(self.database_path)

    if self.get_result("""SELECT * FROM sqlite_master
                          WHERE type = ? AND name = ?;
                       """, ('table', self.name)) is None:
      self.database.execute("""CREATE TABLE "%s" (
        name TEXT PRIMARY KEY,
        uuid TEXT
      );""" % self.name)
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.database.close()

  def get_result(self, request, data):
    results = self.database.execute(request, data)
    return results.fetchone()

  def get_uuid(self, name):
    uuid_value = self.get_result(
      'SELECT * FROM "%s" WHERE name = ?;' % self.name,
      (name, )
    )
    if uuid_value is None:
      uuid_value = uuid.uuid4().urn
      self.database.execute('INSERT INTO "%s" VALUES (?, ?);' % self.name,
                            (name, uuid_value))
      self.database.commit()
    else:
      uuid_value = uuid_value[1]
    return uuid_value


class Recipe(GenericBaseRecipe):


  def _options(self, options):
    with UIDDatabase(self.options['database'], self.name) as database:
      uuid_name_list = [str(name).strip()
                        for name in options['uuids'].split(' ')]
      for uuid_name in uuid_name_list:
        options[str('uuid-%s' % uuid_name)] = str(database.get_uuid(uuid_name))

  def install(self):
    return []
