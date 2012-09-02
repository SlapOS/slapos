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
import os
import subprocess
import pwd

class Recipe(GenericBaseRecipe):
  """Deploy a fully operational boinc architecture."""

  def __init__(self, buildout, name, options):
    #get current slapuser name
    stat_info = os.stat(options['home'].strip())
    options['user'] = pwd.getpwuid(stat_info.st_uid)[0]
    url_base = "http://["+options['ip']+"]:"+options['port']
    project = options['project'].strip()
    root = options['installroot'].strip()
    options['home_page'] = url_base + "/" + project
    options['admin_page'] = url_base + "/" + project + "_ops/"
    options['cronjob'] = os.path.join(root, project+'.cronjob')

    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def _options(self, options):
    #Path of boinc compiled package
    self.package = options['boinc'].strip()
    self.sourcedir = options['source'].strip()
    self.home = options['home'].strip()
    self.project = options['project'].strip()
    self.project_config = options['project-config'].strip()
    self.installroot = options['installroot'].strip()
    self.boinc_egg = os.path.join(self.package, 'lib/python2.7/site-packages')
    self.developegg = options['develop-egg'].strip()
    self.wrapperdir = options['wrapper-dir'].strip()
    self.passwd = options['passwd'].strip()
    self.boinc_httpd_conf = options['boinc-httpd-conf'].strip()
    #Get binary path
    self.svn = options['svn-binary'].strip()
    self.perl = options['perl-binary'].strip()
    self.pythonbin = options['python-binary'].strip()

    #Apache php informations
    self.wwwdata = options['www-data'].strip()
    self.ipv6 = options['ip'].strip()
    self.port = options['port'].strip()
    self.httpd_conf = options['httpd-conf'].strip()
    self.apachewrapper = options['apache-wrapper'].strip()
    self.htpasswd = options['htpasswd'].strip()
    self.apachebin = options['apache-bin'].strip()
    self.phpini = options['php-ini'].strip()
    self.phpbin = options['php-bin'].strip()
    self.wrapperphp = options['php-wrapper'].strip()

    #get Mysql parameters
    self.username = options['mysql-username'].strip()
    self.password = options['mysql-password'].strip()
    self.database = options['mysql-database'].strip()
    self.mysqlhost = options['mysql-host'].strip()
    self.mysqlport = options['mysql-port'].strip()

  def install(self):
    path_list = []
    make_project = os.path.join(self.package, 'bin/make_project')
    niceprojectname = self.project + "@Home"
    url_base = "http://["+self.ipv6+"]:"+self.port
    slapuser = self.options['user']

    #generate project config file
    configuration = dict(mypassword=self.password,
                    dbname=self.database, hosturl=url_base,
                    boincproject=niceprojectname, installroot=self.installroot,
                    project=self.project)
    config_file = self.createFile(self.project_config,
        self.substituteTemplate(self.getTemplateFilename('project.conf.in'),
        configuration))
    path_list.append(config_file)

    #Define environment variable here
    python_path = self.boinc_egg + ":" + os.environ['PYTHONPATH']
    for f in os.listdir(self.developegg):
      dir = os.path.join(self.developegg, f)
      if os.path.isdir(dir):
        python_path += ":" + dir
    bin_dir = os.path.join(self.home, 'bin')
    environment = dict(
        PATH=self.svn + ':' + bin_dir + ':' + self.perl + ':' + os.environ['PATH'],
        PYTHONPATH=python_path,
        PYTHON=self.pythonbin
    )

    #Regenerate Apache wrapper with current conf and environment variables
    if os.path.exists(self.apachewrapper):
      os.unlink(self.apachewrapper)
    boinc_httpd = self.createFile(os.path.join(self.home, 'etc/httpd_boinc.conf'),
        self.substituteTemplate(self.getTemplateFilename('apache.part.in'),
        dict(project=self.project, niceprojectname=niceprojectname,
            installroot=self.installroot)))
    path_list.append(boinc_httpd)
    httpd_configuration = open(self.boinc_httpd_conf, 'w')
    httpd_configuration.write(open(self.httpd_conf, 'r').read())
    httpd_configuration.write(open(boinc_httpd, 'r').read())
    httpd_configuration.close()

    apache_args = [self.apachebin, '-f', self.boinc_httpd_conf,
         '-DFOREGROUND']
    apache_wrapper = self.createPythonScript(self.apachewrapper,
        'slapos.recipe.librecipe.execute.executee',
        (apache_args, environment)
    )
    path_list.append(apache_wrapper)

    #Generate wrapper for php
    php_wrapper = self.createPythonScript(self.wrapperphp,
        'slapos.recipe.librecipe.execute.executee',
        ([self.phpbin, '-c', self.phpini], os.environ)
    )
    path_list.append(php_wrapper)

    #Generate python script for MySQL database marker (starting)
    file_status = os.path.join(self.home, '.boinc_config')
    if os.path.exists(file_status):
      os.unlink(file_status)
    mysql_wrapper = self.createPythonScript(
      os.path.join(self.wrapperdir, 'start_config'),
      '%s.configure.checkMysql' % __name__,
      dict(mysql_port=self.mysqlport, mysql_host=self.mysqlhost,
          mysql_user=self.username, mysql_password=self.password,
          database=self.database,
          file_status=file_status, python_path=python_path
      )
    )

    # Generate make project wrapper file
    launch_args = [make_project, '--url_base', url_base, "--db_name",
              self.database, "--db_user", self.username, "--db_passwd",
              self.password, "--project_root", self.installroot, "--db_host",
              self.mysqlhost, "--user_name", slapuser, "--srcdir",
              self.sourcedir, "--no_query", "--delete_prev_inst",
              "--drop_db_first", self.project, niceprojectname]

    install_wrapper = self.createPythonScript(os.path.join(self.wrapperdir,
        'make_project'),
        'slapos.recipe.librecipe.execute.executee_wait',
        (launch_args, [file_status], environment)
    )
    path_list.append(install_wrapper)

    #After make_project run configure_script to perform and restart apache php services
    service_status = os.path.join(self.home, '.start_service')
    if os.path.exists(service_status):
      os.unlink(service_status)
    parameter = dict(
        readme=os.path.join(self.installroot, self.project+'.readme'),
        htpasswd=self.htpasswd,
        installroot=self.installroot,
        username=slapuser,
        passwd=self.passwd,
        xadd=os.path.join(self.installroot, 'bin/xadd'),
        environment=environment,
        service_status=service_status,
        project=niceprojectname
    )
    start_service = self.createPythonScript(
      os.path.join(self.wrapperdir, 'config_project'),
      '%s.configure.services' % __name__, parameter
    )
    path_list.append(start_service)

    #Generate Boinc project wrapper
    start_args = [os.path.join(self.installroot, 'bin/start')]
    start_wrapper = self.createPythonScript(os.path.join(self.wrapperdir,
        'start_project'),
        'slapos.recipe.librecipe.execute.executee_wait',
        (start_args, [service_status], environment)
    )
    path_list.append(start_wrapper)

    return path_list

  update=install
