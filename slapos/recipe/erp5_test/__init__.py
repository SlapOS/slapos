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
    # functional yet in slapos: test_0...test_100, with same user name
    mysql_template = "%s@%s:%s %s %s"
    mysql_parsed = urlparse.urlparse(self.options['mysql-url'])
    for i in range(0, 100):
      mysql_connection_string_list.append(mysql_template % ('test_%s'% i,
        mysql_parsed.hostname, mysql_parsed.port, 'test_%s'% i, mysql_parsed.password))
    mysql_connection_string = mysql_template % ('erp5_test', mysql_parsed.hostname,
      mysql_parsed.port, 'erp5_test', mysql_parsed.password)
    cloudooo_parsed = urlparse.urlparse(self.options['cloudooo-url'])
    memcached_parsed = urlparse.urlparse(self.options['memcached-url'])
    kumofs_parsed = urlparse.urlparse(self.options['kumofs-url'])
    path_list.append(self.createPythonScript(self.options['run-unit-test'],
        __name__ + '.test.runUnitTest', [dict(
        instance_home=testinstance,
        prepend_path=self.options['prepend-path'],
        openssl_binary=self.options['openssl-binary'],
        test_ca_path=self.options['certificate-authority-path'],
        call_list=[self.options['run-unit-test-binary'],
          '--erp5_sql_connection_string', mysql_connection_string,
          '--extra_sql_connection_string_list', ','.join(
            mysql_connection_string_list),
          '--conversion_server_hostname=%s' % cloudooo_parsed.hostname,
          '--conversion_server_port=%s' % cloudooo_parsed.port,
          '--volatile_memcached_server_hostname=%s' % memcached_parsed.hostname,
          '--volatile_memcached_server_port=%s' % memcached_parsed.port,
          '--persistent_memcached_server_hostname=%s' % kumofs_parsed.hostname,
          '--persistent_memcached_server_port=%s' % kumofs_parsed.port,
      ])]))

    return path_list

#  def installTestSuiteRunner(self, ca_conf, mysql_conf, conversion_server_conf,
#                        memcached_conf, kumo_conf):
#    """Installs bin/runTestSuite executable to run all tests using
#       bin/runUnitTest"""
#    testinstance = self.createDataDirectory('test_suite_instance')
#    # workaround wrong assumptions of ERP5Type.tests.runUnitTest about
#    # directory existence
#    unit_test = os.path.join(testinstance, 'unit_test')
#    if not os.path.isdir(unit_test):
#      os.mkdir(unit_test)
#    mysql_connection_string_list = []
#    for test_database, test_user, test_password in \
#        mysql_conf['mysql_parallel_test_dict']:
#      mysql_connection_string_list.append(
#          '%s@%s:%s %s %s' % (test_database, mysql_conf['ip'],
#                              mysql_conf['tcp_port'], test_user, test_password))
#    command = zc.buildout.easy_install.scripts([
#      ('runTestSuite', __name__ + '.test_suite_runner', 'runTestSuite')],
#      self.ws, sys.executable, self.bin_directory, arguments=[dict(
#        instance_home=testinstance,
#        prepend_path=self.bin_directory,
#        openssl_binary=self.options['openssl_binary'],
#        test_ca_path=ca_conf['certificate_authority_path'],
#        call_list=[self.options['runTestSuite_binary'],
#          '--db_list', ','.join(mysql_connection_string_list),
#          '--conversion_server_hostname=%(conversion_server_ip)s' % \
#                                                         conversion_server_conf,
#          '--conversion_server_port=%(conversion_server_port)s' % \
#                                                         conversion_server_conf,
#          '--volatile_memcached_server_hostname=%(memcached_ip)s' % memcached_conf,
#          '--volatile_memcached_server_port=%(memcached_port)s' % memcached_conf,
#          '--persistent_memcached_server_hostname=%(kumo_gateway_ip)s' % kumo_conf,
#          '--persistent_memcached_server_port=%(kumo_gateway_port)s' % kumo_conf,
#      ]
#        )])[0]
#    self.path_list.append(command)


