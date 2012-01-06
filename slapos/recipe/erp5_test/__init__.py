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
from slapos.recipe.librecipe import GenericBaseRecipe
import urlparse

class Recipe(GenericBaseRecipe):
  def install(self):
    testinstance = self.options['test-instance-path']
    mysql_connection_string_list = []
    path_list = []
    # XXX: assume existence of 100 test databases, because slaves are not
    # functional yet in slapos: testdb_0...testdb_100, with testuser_N
    mysql_template = "%s@%s:%s %s %s"
    mysql_parsed = urlparse.urlparse(self.options['mysql-url'])
    for i in range(0, 100):
      mysql_connection_string_list.append(mysql_template % ('testdb_%s'% i,
        mysql_parsed.hostname, mysql_parsed.port, 'testuser_%s'% i, mysql_parsed.password))
    mysql_connection_string = mysql_template % ('erp5_test', mysql_parsed.hostname,
      mysql_parsed.port, 'erp5_test', mysql_parsed.password)
    cloudooo_parsed = urlparse.urlparse(self.options['cloudooo-url'])
    memcached_parsed = urlparse.urlparse(self.options['memcached-url'])
    kumofs_parsed = urlparse.urlparse(self.options['kumofs-url'])
    common_dict = dict(
        instance_home=testinstance,
        prepend_path=self.options['prepend-path'],
        openssl_binary=self.options['openssl-binary'],
        test_ca_path=self.options['certificate-authority-path'],
    )
    common_list = [
      '--conversion_server_hostname=%s' % cloudooo_parsed.hostname,
      '--conversion_server_port=%s' % cloudooo_parsed.port,
      '--volatile_memcached_server_hostname=%s' % memcached_parsed.hostname,
      '--volatile_memcached_server_port=%s' % memcached_parsed.port,
      '--persistent_memcached_server_hostname=%s' % kumofs_parsed.hostname,
      '--persistent_memcached_server_port=%s' % kumofs_parsed.port,
    ]
    path_list.append(self.createPythonScript(self.options['run-unit-test'],
        __name__ + '.test.runUnitTest', [dict(
        call_list=[self.options['run-unit-test-binary'],
          '--erp5_sql_connection_string', mysql_connection_string,
          '--extra_sql_connection_string_list', ','.join(
            mysql_connection_string_list),
          ] + common_list, **common_dict)]))
    path_list.append(self.createPythonScript(self.options['run-test-suite'],
        __name__ + '.test.runUnitTest', [dict(
        call_list=[self.options['run-test-suite-binary'],
          '--db_list', ','.join(mysql_connection_string_list),
          ] + common_list, **common_dict)]))

    return path_list
