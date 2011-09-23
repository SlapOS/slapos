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
import zc.buildout
import sys
import zc.recipe.egg

class BaseRecipe(BaseSlapRecipe):
  def installMysqlServer(self, ip=None, port=None):
    if ip is None:
      ip = self.getLocalIPv4Address()
    if port is None:
      port = '3306'
    mysql_conf = dict(
        ip=ip,
        data_directory=os.path.join(self.data_root_directory,
          'mysql'),
        tcp_port=port,
        pid_file=os.path.join(self.run_directory, 'mysqld.pid'),
        socket=os.path.join(self.run_directory, 'mysqld.sock'),
        error_log=os.path.join(self.log_directory, 'mysqld.log'),
        slow_query_log=os.path.join(self.log_directory,
        'mysql-slow.log'),
        database='appdb',
        user='appuser',
        password=self.generatePassword(),
    )
    self._createDirectory(mysql_conf['data_directory'])

    mysql_conf_path = self.createConfigurationFile("my.cnf",
        self.substituteTemplate(pkg_resources.resource_filename(__name__, 'template/my.cnf.in'),
          mysql_conf))

    mysql_script = pkg_resources.resource_string(__name__,
        'template/mysqlinit.sql.in') % mysql_conf
    self.path_list.extend(zc.buildout.easy_install.scripts([('mysql_update',
      __name__ + '.mysql', 'updateMysql')], self.ws,
      sys.executable, self.wrapper_directory, arguments=[dict(
        mysql_script=mysql_script,
        mysql_binary=self.options['mysql_binary'].strip(),
        mysql_upgrade_binary=self.options['mysql_upgrade_binary'].strip(),
        socket=mysql_conf['socket'],
        )]))
    self.path_list.extend(zc.buildout.easy_install.scripts([('mysqld',
      __name__ + '.mysql', 'runMysql')], self.ws,
        sys.executable, self.wrapper_directory, arguments=[dict(
        mysql_install_binary=self.options['mysql_install_binary'].strip(),
        mysqld_binary=self.options['mysqld_binary'].strip(),
        data_directory=mysql_conf['data_directory'].strip(),
        mysql_binary=self.options['mysql_binary'].strip(),
        socket=mysql_conf['socket'].strip(),
        configuration_file=mysql_conf_path,
       )]))
    self.path_list.extend([mysql_conf_path])
    return dict(
      mysql_host=mysql_conf['ip'],
      mysql_port=mysql_conf['tcp_port'],
      mysql_user=mysql_conf['user'],
      mysql_password=mysql_conf['password'],
      mysql_database=mysql_conf['database'],
    )

  def createHtdocs(self, source, document_root):
    source = self.options['source'].strip()
    document_root = self.createDataDirectory('htdocs')
    for p in os.listdir(document_root):
      path = os.path.join(document_root, p)
      if os.path.isdir(path):
        shutil.rmtree(path)
      else:
        os.unlink(path)
    for p in os.listdir(source):
      path = os.path.join(source, p)
      if os.path.isdir(path):
        shutil.copytree(path, os.path.join(document_root, p))
      else:
        shutil.copy2(path, os.path.join(document_root, p))

  def installApache(self, document_root, ip=None, port=None):
    if ip is None:
      ip=self.getGlobalIPv6Address()
    if port is None:
      port = '9080'
    apache_config = dict(
        pid_file=os.path.join(self.run_directory, 'httpd.pid'),
        lock_file=os.path.join(self.run_directory, 'httpd.lock'),
        ip=ip,
        port=port,
        error_log=os.path.join(self.log_directory, 'httpd-error.log'),
        access_log=os.path.join(self.log_directory, 'httpd-access.log'),
        document_root=document_root,
        php_ini_dir=self.etc_directory
    )
    config_file = self.createConfigurationFile('httpd.conf',
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          'template/apache.in'), apache_config))
    self.path_list.append(config_file)
    self.path_list.append(self.createConfigurationFile('php.ini',
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          'template/php.ini.in'), dict(tmp_directory=self.tmp_directory))))
    self.path_list.extend(zc.buildout.easy_install.scripts([(
      'httpd',
        __name__ + '.apache', 'runApache')], self.ws,
          sys.executable, self.wrapper_directory, arguments=[
            dict(
              required_path_list=[],
              binary=self.options['httpd_binary'],
              config=config_file
            )
          ]))
    return 'http://[%s]:%s' % (ip, port)

  def createConfiguration(self, template, document_root, destination, d):
    directory = os.path.dirname(destination)
    file = os.path.basename(destination)
    path = document_root
    if directory:
      path = os.path.join(document_root, directory)
      if not os.path.exists(path):
        os.makedirs(path)
    destination = os.path.join(path, file)
    open(destination, 'w').write(open(template, 'r').read() % d)

class Static(BaseRecipe):
  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    document_root = self.createDataDirectory('htdocs')
    self.createHtdocs(self.options['source'].strip(), document_root)
    url = self.installApache(document_root)
    self.setConnectionDict(dict(url = url))
    return self.path_list

class Simple(BaseRecipe):
  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    document_root = self.createDataDirectory('htdocs')
    self.createHtdocs(self.options['source'].strip(), document_root)
    mysql_conf = self.installMysqlServer()
    url = self.installApache(document_root)
    self.setConnectionDict(dict(
      url=url,
      **mysql_conf
    ))
    self.createConfiguration(self.options['template'], document_root,
        self.options['configuration'], mysql_conf)
    return self.path_list

class Request(BaseRecipe):
  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    software_type = self.parameter_dict['slap_software_type']
    if software_type == 'RootSoftwareInstance':
      document_root = self.createDataDirectory('htdocs')
      self.createHtdocs(self.options['source'].strip(), document_root)
      mysql = self.request(self.software_release_url, 'MySQL Server', 'mysql')
      mysql_conf = dict(
        mysql_host=mysql.getConnectionParameter('mysql_host'),
        mysql_port=mysql.getConnectionParameter('mysql_port'),
        mysql_user=mysql.getConnectionParameter('mysql_user'),
        mysql_password=mysql.getConnectionParameter('mysql_password'),
        mysql_database=mysql.getConnectionParameter('mysql_database'),
      )
      url = self.installApache(document_root)
      self.setConnectionDict(dict(
        url=url,
      ))
      self.createConfiguration(self.options['template'], document_root,
          self.options['configuration'], mysql_conf)
    elif software_type == 'MySQL Server':
      mysql_conf = self.installMysqlServer()
      self.setConnectionDict(dict(
        **mysql_conf
      ))
    else:
      raise zc.buildout.UserError('Uknown software type %r' % software_type)
    return self.path_list
