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
from slapos.recipe.librecipe import BaseSlapRecipe
import os
import shutil
import pkg_resources
import subprocess
import time
import zc.buildout

class Recipe(BaseSlapRecipe):

  def _install(self):
    self.requirements, self.ws = self.egg.working_set()
    parameter_dict = self.computer_partition.getInstanceParameterDict()
    ipv4 = self.getLocalIPv4Address()
    ipv6 = self.getGlobalIPv6Address()

    self.install_mysql_server_configuration(ipv4)

    port = '8900'
    tomcat_home = os.path.join(self.data_root_directory, 'tomcat')
    tomcat_lib = os.path.join(tomcat_home, 'lib')
    xwiki_home = os.path.join(tomcat_home, 'webapps', 'xwiki')
    for src, dst in (
        (self.options['tomcat_location'].strip(), tomcat_home),
        (self.options['xwiki_location'].strip(), xwiki_home),
        ):
      if not os.path.isdir(dst):
        try:
          shutil.copytree(src, dst)
        except:
          shtuil.rmtree(dst)
          raise

    shutil.copy(self.options['jdbc_location'].strip(), os.path.join(tomcat_lib,
      'jdbc.jar'))
    # headless mode
    self._writeFile(os.path.join(tomcat_home, 'bin', 'setenv.sh'), '''#!/bin/sh
export JAVA_OPTS="${JAVA_OPTS} -Djava.awt.headless=true"
''')
    # tomcat wrapper
    catalina = os.path.join(tomcat_home, 'bin', 'catalina.sh')
    # solve "The BASEDIR environment variable is not defined correctly"
    bindir = os.path.join(tomcat_home, 'bin')
    for f in os.listdir(bindir):
      if f.endswith('.sh'):
        os.chmod(os.path.join(bindir, f), 0755)
    tomcat_wrapper = self.createRunningWrapper('xwiki', """#!/bin/sh
export JRE_HOME=%(java_home)s
exec %(catalina)s run
""" % dict(java_home=self.options['java_home'].strip(),
  catalina = catalina))

    tomcat_dict = dict(
      http_address=ipv6,
      http_port=port,
      ajp_address=ipv4,
      ajp_port="8009",
        )
    server_xml = os.path.join(tomcat_home, 'conf', 'server.xml')
    self._writeFile(server_xml, pkg_resources.resource_string(__name__,
      'template/tomcat-server.xml.in') % tomcat_dict)

    hibernate_xml = os.path.join(tomcat_home, 'webapps', 'xwiki', 'WEB-INF', 'hibernate.cfg.xml')
    self._writeFile(hibernate_xml, pkg_resources.resource_string(__name__,
      'template/hibernate.cfg.xml.in') % dict(mysql_port='45678', mysql_ip = ipv4))

    self.computer_partition.setConnectionDict(dict(
      http_connection="http://[%s]:%s/xwiki/" % (ipv6, port),
      ))
    return [server_xml, tomcat_wrapper]

  def _initializeMysqlServer(self):
    # XXX: Protect with proper root password
    popen = subprocess.Popen([self.options['mysql_install_binary'],
      '--skip-name-resolve', '--no-defaults',
      '--datadir=%s' % self.data_directory],
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = popen.communicate()[0]
    if popen.returncode is None or popen.returncode != 0:
      message = """Failed to initialise server in %(data_directory)r.
The error was: %(result)s""" % dict(data_directory=self.data_directory,
        result=result)
      raise zc.buildout.UserError(message)

  def install_mysql_server_configuration(self, ip):
    self.data_directory = os.path.join(self.data_root_directory,
        'mysql_server')
    self.configuration_file = os.path.join(self.etc_directory, 'my.cnf')
    self._createDirectory(self.data_directory)
    self.options['ip'] = ip
    port = '45678'
    self.options['tcp_port'] = port
    self.options['data_directory'] = self.data_directory
    self.options['pid_file'] = os.path.join(self.run_directory, 'mysqld.pid')
    self.options['socket'] = os.path.join(self.run_directory, 'mysqld.sock')
    self.options['error_log'] = os.path.join(self.log_directory, 'mysqld.log')
    self.options['slow_query_log'] = os.path.join(self.log_directory,
        'mysql-slow.log')
    self._initializeMysqlServer()

    mysql_conf_path = self.createConfigurationFile("my.cnf",
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          os.path.join('template', 'my.cnf.in')), self.options))
    mysql_wrapper_path = self.createRunningWrapper('mysqld',
        pkg_resources.resource_string(__name__, os.path.join('template',
          'mysqld.bin')) % {'configuration_file': self.configuration_file,
                        'real_binary': self.options['mysqld_binary']})

    mysql_connection_dict = dict(
        ip=ip,
        port=port,
        user='xwiki',
        password='xwiki',
        database='xwiki',
        )
    # XXX: Bad thing -- it is required to fill mysql with some data, but there
    #      is no known any way to do it w/o running mysql (except rewriting
    #      mysql_install_db)
    mysqld = subprocess.Popen([mysql_wrapper_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
      # XXX: Simplification of bad idea -- wait some time before connecting to
      #      mysql
      time.sleep(2)
      mysql = subprocess.Popen([self.options['mysql_binary'].strip(),
        '--no-defaults', '-B', '--user=root',
        '--socket=%s' % self.options['socket'],
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
      result = mysql.communicate(pkg_resources.resource_string(__name__,
        'template/initmysql.sql.in') % mysql_connection_dict)[0]
      if mysql.returncode is None:
        mysql.kill()
      if mysql.returncode != 0:
        raise zc.buildout.UserError('Issue during filling database, mysql '
            'command result was: %s' % result)
    finally:
      mysqld.kill()
    self.computer_partition.setConnectionDict(mysql_connection_dict)

    return [mysql_conf_path, mysql_wrapper_path]

