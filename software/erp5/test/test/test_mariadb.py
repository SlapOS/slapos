##############################################################################
# coding: utf-8
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
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
import json
import glob
import urlparse
import socket
import time
import contextlib
import datetime

import MySQLdb

from . import ERP5InstanceTestCase
from . import setUpModule
setUpModule  # pyflakes


class MariaDBTestCase(ERP5InstanceTestCase):
  """Base test case for mariadb tests.
  """
  __partition_reference__ = 'm'

  @classmethod
  def getInstanceSoftwareType(cls):
    return "mariadb"

  @classmethod
  def _getInstanceParameterDict(cls):
    return {
        'tcpv4-port': 3306,
        'max-connection-count': 5,
        'max-slowqueries-threshold': 5,
        'slowest-query-threshold': 10,
        # XXX what is this ? should probably not be needed here
        'name': cls.__name__,
        'monitor-passwd': 'secret',
        # XXX should probably not be needed here
        'computer-memory-percent-threshold': 100,
    }

  @classmethod
  def getInstanceParameterDict(cls):
    return {'_': json.dumps(cls._getInstanceParameterDict())}

  def getDatabaseConnection(self):
    connection_parameter_dict = json.loads(
        self.computer_partition.getConnectionParameterDict()['_'])
    db_url = urlparse.urlparse(connection_parameter_dict['database-list'][0])
    self.assertEqual('mysql', db_url.scheme)

    self.assertTrue(db_url.path.startswith('/'))
    database_name = db_url.path[1:]
    return MySQLdb.connect(
        user=db_url.username,
        passwd=db_url.password,
        host=db_url.hostname,
        port=db_url.port,
        db=database_name,
    )


class TestMariaDB(MariaDBTestCase):
  def test_utf8_collation(self):
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query(
          """
          CREATE TABLE test_utf8_collation (
            col1 CHAR(10)
          )
          """)

      cnx.store_result()
      cnx.query(
          """
          insert into test_utf8_collation values ("à"), ("あ")
          """)
      cnx.store_result()

      cnx.query(
          """
          select * from test_utf8_collation where col1 = "a"
          """)
      self.assertEqual((('à',),), cnx.store_result().fetch_row(maxrows=2))


class TestMroonga(MariaDBTestCase):
  def test_mroonga_plugin_loaded(self):
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query("show plugins")
      plugins = cnx.store_result().fetch_row(maxrows=1000)
      self.assertIn(
          ('Mroonga', 'ACTIVE', 'STORAGE ENGINE', 'ha_mroonga.so', 'GPL'),
          plugins)

  def test_mroonga_normalize_udf(self):
    # example from https://mroonga.org/docs/reference/udf/mroonga_normalize.html#usage
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query(
          """
          SELECT mroonga_normalize("ABCDあぃうぇ㍑")
          """)
      self.assertEqual((('abcdあぃうぇリットル',),),
                       cnx.store_result().fetch_row(maxrows=2))

      if 0:
        # this example fail with:
        # OperationalError: (1123, "Can't initialize function 'mroonga_normalize'; mroonga_normalize(): nonexistent normalizer NormalizerMySQLUnicodeCIExceptKanaCI")
        # same error on mroonga "official" docker images using mysql
        # https://hub.docker.com/layers/groonga/mroonga/latest/images/sha256-e5a979801c95544ca3a1228d2c4d819820850e0162649553f2e94850e5e1c988?context=explore
        # so it's probably OK to ignore
        cnx.query(
            """
            SELECT mroonga_normalize("aBｃＤあぃウェ㍑", "NormalizerMySQLUnicodeCIExceptKanaCIKanaWithVoicedSoundMark")
            """)
        self.assertEqual((('ABCDあぃうぇ㍑',),),
                         cnx.store_result().fetch_row(maxrows=2))

  def test_mroonga_full_text_normalizer(self):
    # example from https://mroonga.org//docs/tutorial/storage.html#how-to-specify-the-normalizer
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):

      cnx.query("SET NAMES utf8")
      cnx.store_result()
      cnx.query(
          """
          CREATE TABLE diaries (
            day DATE PRIMARY KEY,
            content VARCHAR(64) NOT NULL,
            FULLTEXT INDEX (content) COMMENT 'normalizer "NormalizerAuto"'
          ) Engine=Mroonga DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
          """)
      cnx.store_result()
      cnx.query(
          """INSERT INTO diaries VALUES ("2013-04-23", "ブラックコーヒーを飲んだ。")""")
      cnx.store_result()
      cnx.query(
          """
          SELECT *
            FROM diaries
           WHERE MATCH (content) AGAINST ("+ふらつく" IN BOOLEAN MODE)
          """)
      self.assertEqual((), cnx.store_result().fetch_row(maxrows=2))
      cnx.query(
          """
          SELECT *
            FROM diaries
           WHERE MATCH (content) AGAINST ("+ﾌﾞﾗｯｸ" IN BOOLEAN MODE)
          """)
      self.assertEqual(
          ((datetime.date(2013, 4, 23), 'ブラックコーヒーを飲んだ。'),),
          cnx.store_result().fetch_row(maxrows=2),
      )

  def test_mroonga_full_text_stem(self):
    # example from https://mroonga.org//docs/tutorial/storage.html#how-to-specify-the-token-filters
    cnx = self.getDatabaseConnection()
    with contextlib.closing(cnx):
      cnx.query("SELECT mroonga_command('register token_filters/stem')")
      self.assertEqual((('true',),), cnx.store_result().fetch_row(maxrows=2))
      cnx.query(
          """
          CREATE TABLE memos (
            id INT NOT NULL PRIMARY KEY,
            content TEXT NOT NULL,
            FULLTEXT INDEX (content) COMMENT 'normalizer "NormalizerAuto", token_filters "TokenFilterStem"'
          ) Engine=Mroonga DEFAULT CHARSET=utf8
          """)
      cnx.store_result()
      cnx.query(
          """INSERT INTO memos VALUES (1, "I develop Groonga"), (2, "I'm developing Groonga"), (3, "I developed Groonga")"""
      )
      cnx.store_result()
      cnx.query(
          """
          SELECT *
            FROM memos
           WHERE MATCH (content) AGAINST ("+develops" IN BOOLEAN MODE)
          """)
      self.assertEqual([
          (1, "I develop Groonga"),
          (2, "I'm developing Groonga"),
          (3, "I developed Groonga"),
      ], list(sorted(cnx.store_result().fetch_row(maxrows=4))))
