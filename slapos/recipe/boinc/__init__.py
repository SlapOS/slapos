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
import signal

class Recipe(GenericBaseRecipe):
  """Deploy a fully operational boinc architecture."""

  def __init__(self, buildout, name, options):
    #get current slapuser name
    stat_info = os.stat(options['home'].strip())
    options['user'] = pwd.getpwuid(stat_info.st_uid)[0]
    url_base = options['url-base']
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
    self.fullname = options['fullname'].strip()
    self.copyright = options['copyright'].strip()
    self.installroot = options['installroot'].strip()
    self.boinc_egg = os.path.join(self.package, 'lib/python2.7/site-packages')
    self.developegg = options['develop-egg'].strip()
    self.wrapperdir = options['wrapper-dir'].strip()
    self.passwd = options['passwd'].strip()
    #Get binary path
    self.svn = options['svn-binary'].strip()
    self.perl = options['perl-binary'].strip()
    self.pythonbin = options['python-binary'].strip()

    #Apache php informations
    self.url_base =options['url-base'].strip()
    self.htpasswd = options['htpasswd'].strip()
    self.phpini = options['php-ini'].strip()
    self.phpbin = options['php-bin'].strip()

    #get Mysql parameters
    self.username = options['mysql-username'].strip()
    self.password = options['mysql-password'].strip()
    self.database = options['mysql-database'].strip()
    self.mysqlhost = options['mysql-host'].strip()
    self.mysqlport = options['mysql-port'].strip()

  def haschanges(self):
    config_file = os.path.join(self.home, '.config')
    current = [self.fullname, self.copyright,
        self.password, self.mysqlhost, self.installroot,
        self.project, self.passwd, self.url_base]
    previous = []
    result = False
    if os.path.exists(config_file):
      previous = open(config_file, 'r').read().split('#')
    #Check if config has changed
    if len(current) != len(set(current).intersection(set(previous))) or \
        not os.path.exists(self.installroot) or \
        not os.path.exists(os.path.join(self.home, '.start_service')):
      result = True
    open(config_file, 'w').write('#'.join(current))
    return result

  def install(self):
    path_list = []
    make_project = os.path.join(self.package, 'bin/make_project')
    niceprojectname = self.project + "@Home"
    slapuser = self.options['user']

    #Define environment variable here
    python = os.path.join(self.home, 'bin/python')
    python_path = self.boinc_egg + ":" + os.environ['PYTHONPATH']
    if not os.path.exists(python):
      os.symlink(self.pythonbin, python)
    for f in os.listdir(self.developegg):
      dir = os.path.join(self.developegg, f)
      if os.path.isdir(dir):
        python_path += ":" + dir
    bin_dir = os.path.join(self.home, 'bin')
    environment = dict(
        PATH=self.svn + ':' + bin_dir + ':' + self.perl + ':' + os.environ['PATH'],
        PYTHONPATH=python_path,
    )

    #Generate wrapper for php
    wrapperphp = os.path.join(self.home, 'bin/php')
    php_wrapper = self.createPythonScript(wrapperphp,
        'slapos.recipe.librecipe.execute.executee',
        ([self.phpbin, '-c', self.phpini], os.environ)
    )
    path_list.append(php_wrapper)

    #Generate python script for MySQL database test (starting)
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
    readme_file = os.path.join(self.installroot, self.project+'.readme')
    launch_args = [make_project, '--url_base', self.url_base, "--db_name",
              self.database, "--db_user", self.username, "--db_passwd",
              self.password, "--project_root", self.installroot, "--db_host",
              self.mysqlhost, "--user_name", slapuser, "--srcdir",
              self.sourcedir, "--no_query"]
    drop_install = self.haschanges()
    if drop_install:
      #Allow to restart Boinc installation from the begining
      launch_args += ["--delete_prev_inst", "--drop_db_first"]
      if os.path.exists(readme_file):
        os.unlink(readme_file)
    launch_args += [self.project, niceprojectname]

    install_wrapper = self.createPythonScript(os.path.join(self.wrapperdir,
        'make_project'),
        'slapos.recipe.librecipe.execute.executee_wait',
        (launch_args, [file_status], environment)
    )
    path_list.append(install_wrapper)

    #After make_project run configure_script to perform and restart apache php services
    service_status = os.path.join(self.home, '.start_service')
    parameter = dict(
        readme=readme_file,
        htpasswd=self.htpasswd,
        installroot=self.installroot,
        username=slapuser,
        passwd=self.passwd,
        xadd=os.path.join(self.installroot, 'bin/xadd'),
        environment=environment,
        service_status=service_status,
        project=niceprojectname,
        fullname=self.fullname,
        copyright=self.copyright,
        drop_install=drop_install
    )
    start_service = self.createPythonScript(
      os.path.join(self.wrapperdir, 'config_project'),
      '%s.configure.services' % __name__, parameter
    )
    path_list.append(start_service)

    #Generate Boinc start project wrapper
    start_args = [os.path.join(self.installroot, 'bin/start')]
    start_boinc = os.path.join(self.home, '.start_boinc')
    if os.path.exists(start_boinc):
      os.unlink(start_boinc)
    boinc_parameter = dict(service_status=service_status,
        installroot=self.installroot, drop_install=drop_install,
        mysql_port=self.mysqlport, mysql_host=self.mysqlhost,
        mysql_user=self.username, mysql_password=self.password,
        database=self.database, PATH=environment['PATH'],
        python_path=python_path, start_boinc=start_boinc)
    start_wrapper = self.createPythonScript(os.path.join(self.wrapperdir,
        'start_boinc'),
        '%s.configure.restart_boinc' % __name__,
        boinc_parameter
    )
    path_list.append(start_wrapper)

    return path_list

  update = install


class App(GenericBaseRecipe):
  """This recipe allow to deploy an scientific applications using boinc
  Note that recipe use depend on boinc-server parameter"""


  def install(self):
    if self.options['app-name'].strip() == '' or \
              self.options['version'].strip() == '':
      #don't deploy empty application...skipped
      return []
    path_list = []
    package = self.options['boinc'].strip()
    #Define environment variable here
    boinc_egg = os.path.join(package, 'lib/python2.7/site-packages')
    developegg = self.options['develop-egg'].strip()
    python_path = boinc_egg + ":" + os.environ['PYTHONPATH']
    home = self.options['home'].strip()
    perl = self.options['perl-binary'].strip()
    svn = self.options['svn-binary'].strip()
    for f in os.listdir(developegg):
      dir = os.path.join(developegg, f)
      if os.path.isdir(dir):
        python_path += ":" + dir
    bin_dir = os.path.join(home, 'bin')
    environment = dict(
        PATH=svn + ':' + bin_dir + ':' + perl + ':' + os.environ['PATH'],
        PYTHONPATH=python_path,
    )

    #generate project.xml and config.xml script updater
    bash = os.path.join(home, 'bin', 'update_config.sh')
    sh_script = self.createFile(bash,
        self.substituteTemplate(self.getTemplateFilename('sed_update.in'),
        dict(dash=self.options['dash'].strip(),
              uldl_pid=self.options['apache-pid'].strip()))
    )
    path_list.append(sh_script)
    os.chmod(bash , 0700)

    start_boinc = os.path.join(home, '.start_boinc')
    installroot = self.options['installroot'].strip()
    version = self.options['version'].strip()
    platform = self.options['platform'].strip()
    apps_dir = os.path.join(installroot, 'apps')
    appname = self.options['app-name'].strip()
    bin_name = appname +"_"+ version +"_"+ \
        platform +  self.options['extension'].strip()
    application = os.path.join(apps_dir, appname, version, platform)
    wrapperdir = self.options['wrapper-dir'].strip()
    project = self.options['project'].strip()

    parameter = dict(installroot=installroot, project=project,
            appname=appname, binary_name=bin_name,
            version=version, platform=platform,
            application=application, environment=environment,
            start_boinc=start_boinc,
            wu_number=int(self.options['wu-number'].strip()),
            t_result=self.options['template-result'].strip(),
            t_wu=self.options['template-wu'].strip(),
            t_input=self.options['input-file'].strip(),
            binary=self.options['binary'].strip(),
            bash=bash,
    )
    deploy_app = self.createPythonScript(
      os.path.join(wrapperdir, appname),
      '%s.configure.deployApp' % __name__, parameter
    )
    path_list.append(deploy_app)

    return path_list

  update = install

class Client(GenericBaseRecipe):
  """Deploy a fully fonctionnal boinc client connected to a boinc server instance"""

  def install(self):
    path_list = []
    boincbin = self.options['boinc-bin'].strip()
    installdir = self.options['install-dir'].strip()
    url = self.options['server-url'].strip()
    key = self.options['key'].strip()
    boinc_wrapper = self.options['client-wrapper'].strip()

    #Generate wrapper for boinc_client
    client_wrapper = self.createPythonScript(boinc_wrapper,
        'slapos.recipe.librecipe.execute.execute',
        ([boincbin, '--dir', installdir, '--attach_project', url, key])
    )
    path_list.append(client_wrapper)
    return path_list

  update = install
  