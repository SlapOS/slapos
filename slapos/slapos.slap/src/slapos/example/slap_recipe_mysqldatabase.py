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
from slapos.slap import slap, ComputerPartition, ResourceNotReady
import sys
import MySQLDB

class Recipe:
  def __init__(self, buildout, options):
    self.buildout, self.options = buildout, options

  def install(self):
    # register self on slap
    # online computer partition, slap gave connector
    computer_partition = slap(self.options['vifib_server_url']).register(
        ComputerPartition,
        coordinate_kw=dict(
          computer_id=self.options['computer_id'], # c09fba86-b690-493d-b2b5-03a0df580b28
          partition_id=self.options['partition_id'], # 007
          resource_url=self.options['resource_url'], # http://slapgrid.org/resource/mysqldatabase-5.4.5
        )
      )

    # request mysql server instance in version 5.4.5
    mysql_server_partition = computer_partition.request(
      self.options['parent_resource_url'], # http://slapgrid.org/resource/mysqlserver-5.4.5
      self.options['parent_resource_id'], # main_server
    )

    # invoke installation
    try:
      connect = MySQLDB(mysql_server_partition.getIP(),
        mysql_server_partition.getPort(), mysql_server_partition.getUser(),
        mysql_server_partition.getPassword()).connect()
    except ResourceNotReady:
      # accept asynchronous mode
      self.logger.info('Not yet available, postponing...')
      return []

    if not connect.isDatabaseCreated(self.options['database_name']):
      computer_partition.building()
      try:
        connect.query('CREATE DATABASE IF NOT EXISTS %s' %
            self.options['database_name'])
      except:
        # issue during installation
        message = 'Issue during creation %s:%s' % sys.traceback_info_as_list()
        computer_partition.error(message)
        self.logger.error(message)

    if connect.isDatabaseCreated(self.options['database_name']):
      computer_partition.available()

    return []

  update = install
