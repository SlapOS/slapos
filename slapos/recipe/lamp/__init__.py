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
import urlparse

class BaseRecipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

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
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
        'template/my.cnf.in'), mysql_conf))

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
    php_ini = pkg_resources.resource_filename(__name__, 'template/php.ini.in')
    if self.options.has_key('php_ini'):
      php_ini = os.path.join(self.options['php_ini'], 'php.ini.in')
    self.path_list.append(self.createConfigurationFile('php.ini',
        self.substituteTemplate(php_ini, dict(tmp_directory=self.tmp_directory))))
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

  def configureInstallation(self, document_root, url, mysql_conf):
    """Start process which can launch python scripts, move or remove files or 
    directories when installing software.
    """
    if not self.options.has_key('delete') and not self.options.has_key('rename') and not\
        self.options.has_key('chmod') and not self.options.has_key('script'):
      return ""
    delete = []
    chmod = []
    data = []
    rename = []
    rename_list = ""
    argument = [self.options['lampconfigure_directory'].strip(),
                             "-H", mysql_conf['mysql_host'], "-P", mysql_conf['mysql_port'],
                             "-p", mysql_conf['mysql_password'], "-u", mysql_conf['mysql_user']]
    if not self.options.has_key('file_token'):
      argument = argument + ["-d", mysql_conf['mysql_database'],
                             "--table", self.options['table_name'].strip(), "--cond",
                             self.options['constraint'].strip()]
    else:
      argument = argument + ["-f", self.options['file_token'].strip()]
    argument += ["-t", document_root]
    
    if self.options.has_key('delete'):
      delete = ["delete"]
      for fname in self.options['delete'].split(','):
        delete.append(fname.strip())
    if self.options.has_key('rename'):
      for fname in self.options['rename'].split(','):
        if fname.find("=>") < 0:
          old_name = fname
          fname = []
          fname.append(old_name)
          fname.append(old_name + '-' + mysql_conf['mysql_user'])
        else:
          fname = fname.split("=>")
        cmd = ["rename"]
        if self.options.has_key('rename_chmod'):
          cmd += ["--chmod", self.options['rename_chmod'].strip()]
        rename.append(cmd + [fname[0].strip(), fname[1].strip()])
        rename_list += fname[0] + " to " + fname[1] + " "
    if self.options.has_key('chmod'):
      chmod = ["chmod", self.options['mode'].strip()]
      for fname in self.options['chmod'].split(','):
        chmod.append(fname.strip())
    if self.options.has_key('script') and \
        self.options['script'].strip().endswith(".py"):
      data = ["run", self.options['script'].strip(), "-v", mysql_conf['mysql_database'], url, document_root]
    self.path_list.extend(zc.buildout.easy_install.scripts(
        [('configureInstall', __name__ + '.runner', 'executeRunner')], self.ws,
        sys.executable, self.wrapper_directory, arguments=[argument, delete, rename,
            chmod, data]))
    return rename_list

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
    renamed = self.configureInstallation(document_root, url, mysql_conf)
    connectionDict = dict(
      url=url,      
      **mysql_conf
    )
    if not renamed == "":
      connectionDict['rename'] = renamed
    self.setConnectionDict(connectionDict)
    if self.options.has_key('template') and self.options.has_key('configuration'):
      self.createConfiguration(self.options['template'], document_root,
          self.options['configuration'], mysql_conf)
    return self.path_list

class Request(BaseRecipe):
  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    software_type = self.parameter_dict['slap_software_type']

    document_root = self.createDataDirectory('htdocs')
    self.createHtdocs(self.options['source'].strip(), document_root)

    if software_type == 'Backuped':
      davstorage = self.request(self.options['davstorage-software-url'],
        software_type, 'Backup Server').getConnectionParameter('url')

      parameters = {'remote_backup': davstorage}
    elif software_type == 'PersonnalBackup':
      parameters = {'remote_backup': self.parameter_dict['remote_backup']}
    else:
      parameters = {}

    mysql = self.request(self.options['mariadb-software-url'],
      software_type, 'MariaDB Server', partition_parameter_kw=parameters
    ).getConnectionParameter('url')
    mysql_parsed = urlparse.urlparse(mysql)

    mysql_host, mysql_port = mysql_parsed.hostname, mysql_parsed.port
    if mysql_parsed.scheme == 'mysqls': # Listen over stunnel
      mysql_host, mysql_port = self.installStunnelClient(mysql_host,
                                                         mysql_port)

    mysql_conf = dict(mysql_database=mysql_parsed.path.strip('/'),
                      mysql_user=mysql_parsed.username,
                      mysql_password=mysql_parsed.password,
                      mysql_host='%s:%s' % (mysql_host,mysql_port))

    url = self.installApache(document_root)

    self.setConnectionDict(dict(
      url=url,
    ))

    self.createConfiguration(self.options['template'], document_root,
        self.options['configuration'], mysql_conf)
    return self.path_list

  def installStunnelClient(self, remote_host, remote_port):
    local_host = self.getLocalIPv4Address()
    local_port = 8888
    stunnel_conf_path = self.createConfigurationFile('stunnel.conf',
      self.substituteTemplate(
      self.getTemplateFilename('stunnel.conf.in'), {
        'log': os.path.join(self.log_directory, 'stunnel.log'),
        'pid_file': os.path.join(self.run_directory, 'stunnel.pid'),
        'remote_host': remote_host, 'remote_port': remote_port,
        'local_host': local_host, 'local_port': local_port,
      }))
    wrapper = zc.buildout.easy_install.scripts([('stunnel',
      'slapos.recipe.librecipe.execute', 'execute')], self.ws,
      sys.executable, self.wrapper_directory, arguments=[
        self.options['stunnel_binary'].strip(), stunnel_conf_path]
      )[0]
    self.path_list.append(wrapper)
    return (local_host, local_port,)
