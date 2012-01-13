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
import slapos.recipe.erp5
import os
import pkg_resources
import zc.buildout
import sys
import netaddr

def validLoopBackAddress(ip):
  if netaddr.IPAddress(ip).is_loopback():
    return True
  else:
    return False

def validPublicAddress(ip):
  return not validLoopBackAddress(ip)

class Recipe(slapos.recipe.erp5.Recipe):

  def getLocalIPv4Address(self):
    """Returns local IPv4 address available on partition"""
    # XXX: Lack checking for locality of address
    if self.development:
      # XXX: Development superhack.
      return slapos.recipe.erp5.Recipe.getLocalIPv4Address(self)
    return self._getIpAddress(validLoopBackAddress)

  def getGlobalIPv6Address(self):
    """Returns global IPv6 address available on partition"""
    if self.development:
      # XXX: Development superhack.
      return slapos.recipe.erp5.Recipe.getGlobalIPv6Address(self)
    # XXX: Lack checking for globality of address

    return self._getIpAddress(validPublicAddress)

  def installProductionFrontend(self):
    frontend_key, frontend_certificate = self.requestCertificate(
        self.parameter_dict['frontend_name'])
    login_frontend = self.installFrontendZopeApache(
        self.getGlobalIPv6Address(), 18000,
        self.parameter_dict['frontend_name'],
        self.parameter_dict['frontend_path'],
        self.parameter_dict['backend_url'],
        self.parameter_dict['backend_path'], frontend_key,
        frontend_certificate,
        access_control_string=self.parameter_dict['frontend_acl_string'])

    self.setConnectionDict(dict(
      site_url='https://%s:%s%s' % (self.getGlobalIPv6Address(), 18000,
        self.parameter_dict['frontend_path']),
    ))
    return self.path_list

#   def installMysqldumpBackup(self):
#     backup_directory = self.createBackupDirectory('mysqldump')
#     environment = dict(PATH='%s' % self.bin_directory)
#     executable = os.path.join(self.bin_directory, 'mysqldump')
#     mysql_socket = os.path.join(self.var_directory, 'run', 'mysqld.sock')
#     mysqldump_opt = ['-u', 'root', '-S', mysql_socket, '--single-transaction',
#       '--no-autocommit', '--opt']
#     mysqldump_cron = os.path.join(self.cron_d, 'mysqldump')
#     database = 'sanef_dms'
#     cronfile = open(mysqldump_cron, 'w')
#     cronfile.write("0 0 * * * %(mysqldump)s %(mysqldump_opt)s %(database)s | %(gzip)s > %(destination)s\n" % dict(
#       mysqldump=executable, mysqldump_opt=' '.join(mysqldump_opt),
#       database=database, gzip=self.options['gzip_binary'],
#       destination=os.path.join(backup_directory, '%s.sql.gz' % database)
#     ))
#     for table in ['message', 'message_queue', 'portal_ids']:
#       destination = os.path.join(backup_directory, '%s.%s.sql.gz' % (database,
#         table))
#       cronfile.write("0 0 * * * %(mysqldump)s %(mysqldump_opt)s %(database)s %(table)s | %(gzip)s > %(destination)s\n" % dict(
#         mysqldump=executable, mysqldump_opt=' '.join(mysqldump_opt),
#         database=database, gzip=self.options['gzip_binary'],
#         table=table, destination=destination)
#       )
#     cronfile.close()
#     self.path_list.append(mysqldump_cron)
