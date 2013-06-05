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
import json
import signal
import zc.buildout

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
    options['result_page'] = url_base + "/" + project + "_result/"
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

    #Check if given URL is not empty (case of URL request with frontend)
    if not self.url_base:
      raise Exception("URL_BASE is still empty. Can not use it")

    #Define environment variable here
    python = os.path.join(self.home, 'bin/python')
    python_path = self.boinc_egg
    if not os.path.exists(python):
      os.symlink(self.pythonbin, python)
    for f in os.listdir(self.developegg):
      dir = os.path.join(self.developegg, f)
      if os.path.isdir(dir):
        python_path += ":" + dir
    bin_dir = os.path.join(self.home, 'bin')
    environment = dict(
        PATH=os.pathsep.join([self.svn, bin_dir, self.perl, os.environ['PATH']]),
        PYTHONPATH=os.pathsep.join([python_path, os.environ['PYTHONPATH']]),
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
          file_status=file_status, environment=environment
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
    request_make_boinc = os.path.join(self.home, '.make_project')
    if drop_install:
      #Allow to restart Boinc installation from the begining
      launch_args += ["--delete_prev_inst", "--drop_db_first"]
      open(request_make_boinc, 'w').write('Make Requested')
      if os.path.exists(readme_file):
        os.unlink(readme_file)
    launch_args += [self.project, niceprojectname]

    install_wrapper = self.createPythonScript(
      os.path.join(self.wrapperdir, 'make_project'),
      '%s.configure.makeProject' % __name__,
      dict(launch_args=launch_args, request_file=request_make_boinc,
      make_sig=file_status, env=environment)
    )
    path_list.append(install_wrapper)

    #generate sh script for project configuration
    bash = os.path.join(self.home, 'bin', 'project_config.sh')
    sh_script = self.createFile(bash,
        self.substituteTemplate(self.getTemplateFilename('project_config.in'),
        dict(dash=self.options['dash'].strip(),
              uldl_pid=self.options['apache-pid'].strip(),
              user=slapuser, fullname=self.fullname,
              copyright=self.copyright, installroot=self.installroot))
    )
    path_list.append(sh_script)
    os.chmod(bash , 0700)

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
        drop_install=drop_install,
        sedconfig=bash
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
        database=self.database, environment=environment,
        start_boinc=start_boinc)
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

  def downloadFiles(self, app):
    """This is used to download app files if necessary and update options values"""
    for key in ('input-file', 'template-result', 'template-wu', 'binary'):
      param = app[key]
      if param and (param.startswith('http') or param.startswith('ftp')):
        #download the specified file
        cache = os.path.join(self.options['home'].strip(), 'tmp')
        downloader = zc.buildout.download.Download(self.buildout['buildout'],
                        hash_name=True, cache=cache)
        path, _ = downloader(param, md5sum=None)
        mode = 0600
        if key == 'binary':
          mode = 0700
        os.chmod(path, mode)
        app[key] = path

  def getAppList(self):
    """Load parameters,
      check if parameter send is valid to install or update application"""
    app_list = json.loads(self.options['boinc-app-list'])
    if not app_list:
      return None
    default_template_result = self.options.get('default-template-result', '').strip()
    default_template_wu = self.options.get('default-template-wu', '').strip()
    default_extension = self.options.get('default-extension', '').strip()
    default_platform = self.options.get('default-platform', '').strip()
    for app in app_list:
      for version in app_list[app]:
        current_app = app_list[app][version]
        #Use default value if empty and Use_default is True
        #Initialize all values to empty if not define by the user
        if current_app['use_default']:
          current_app['template-result'] = current_app.get('template-result',
                        default_template_result).strip()
          current_app['template-wu'] = current_app.get('template-wu',
                        default_template_wu).strip()
          current_app['extension'] = current_app.get('extension',
                        default_extension).strip()
          current_app['platform'] = current_app.get('platform',
                        default_platform).strip()
        else:
          current_app['template-result'] = current_app.get('template-result', '').strip()
          current_app['template-wu'] = current_app.get('template-wu', '').strip()
          current_app['extension'] = current_app.get('extension', '').strip()
          current_app['platform'] = current_app.get('platform', '').strip()
        current_app['input-file'] = current_app.get('input-file', '').strip()
        current_app['wu-number'] = current_app.get('wu-number', 1)
        #for new application, check if parameter is complete
        appdir = os.path.join(self.options['installroot'].strip(), 'apps',
                        app, version)
        if not os.path.exists(appdir):
          if not current_app['template-result'] or not current_app['binary'] \
              or not current_app['input-file'] or not current_app['template-wu'] \
              or not current_app['platform']:
            print "BOINC-APP: ERROR - Invalid argements values for % ...operation cancelled" % app
            app_list[app][version] = None
            continue
        #write application to install
        request_file = os.path.join(self.options['home'].strip(),
                            '.install_' + app + version)
        toInstall = open(request_file, 'w')
        toInstall.write('install or update')
        toInstall.close()
    return app_list

  def install(self):

    app_list = self.getAppList()

    path_list = []
    package = self.options['boinc'].strip()
    #Define environment variable here
    developegg = self.options['develop-egg'].strip()
    python_path = os.path.join(package, 'lib/python2.7/site-packages')
    home = self.options['home'].strip()
    user = pwd.getpwuid(os.stat(home).st_uid)[0]
    perl = self.options['perl-binary'].strip()
    svn = self.options['svn-binary'].strip()
    for f in os.listdir(developegg):
      dir = os.path.join(developegg, f)
      if os.path.isdir(dir):
        python_path += ":" + dir
    bin_dir = os.path.join(home, 'bin')
    environment = dict(
        PATH=os.pathsep.join([svn, bin_dir, perl, os.environ['PATH']]),
        PYTHONPATH=os.pathsep.join([python_path, os.environ['PYTHONPATH']]),
    )

    #generate project.xml and config.xml script updater
    bash = os.path.join(home, 'bin', 'update_config.sh')
    sh_script = self.createFile(bash,
        self.substituteTemplate(self.getTemplateFilename('sed_update.in'),
        dict(dash=self.options['dash'].strip()))
    )
    path_list.append(sh_script)
    os.chmod(bash , 0700)

    #If useful, download necessary files and update options path
    start_boinc = os.path.join(home, '.start_boinc')
    installroot = self.options['installroot'].strip()
    apps_dir = os.path.join(installroot, 'apps')
    wrapperdir = self.options['wrapper-dir'].strip()
    project = self.options['project'].strip()
    lockfile = os.path.join(self.options['home'].strip(), 'app_install.lock')
    fd = os.open(lockfile, os.O_RDWR|os.O_CREAT)
    os.close( fd )

    for appname in app_list:
      for version in app_list[appname]:
        if not app_list[appname][version]:
          continue
        self.downloadFiles(app_list[appname][version])
        platform = app_list[appname][version]['platform']
        application = os.path.join(apps_dir, appname, version, platform)
        if app_list[appname][version]['binary'] and not platform:
          print "BOINC-APP: WARNING - Cannot specify binary without giving platform value"
          app_list[appname][version]['binary'] = '' #Binary will not be updated

        parameter = dict(installroot=installroot,
                appname=appname, project=project,
                version=version, platform=platform,
                application=application, environment=environment,
                start_boinc=start_boinc,
                wu_number=app_list[appname][version]['wu-number'],
                t_result=app_list[appname][version]['template-result'],
                t_wu=app_list[appname][version]['template-wu'],
                t_input=app_list[appname][version]['input-file'],
                binary=app_list[appname][version]['binary'],
                extension=app_list[appname][version]['extension'],
                bash=bash, home_dir=home,
                lockfile=lockfile,
        )
        deploy_app = self.createPythonScript(
          os.path.join(wrapperdir, 'boinc_%s' % appname),
          '%s.configure.deployApp' % __name__, parameter
        )
        path_list.append(deploy_app)

    return path_list

  update = install

class Client(GenericBaseRecipe):
  """Deploy a fully fonctionnal boinc client connected to a boinc server instance"""

  def __init__(self, buildout, name, options):
    #get current uig to create a unique rpc-port for this client
    stat_info = os.stat(options['home'].strip())
    options['rpc-port'] = pwd.getpwuid(stat_info.st_uid)[2] + 5000

    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def install(self):
    path_list = []
    boincbin = self.options['boinc-bin'].strip()
    cmdbin = self.options['cmd-bin'].strip()
    installdir = self.options['install-dir'].strip()
    url = self.options['server-url'].strip()
    key = self.options['key'].strip()
    boinc_wrapper = self.options['client-wrapper'].strip()
    cmd_wrapper = self.options['cmd-wrapper'].strip()
    remote_host = os.path.join(installdir, 'remote_hosts.cfg')
    open(remote_host, 'w').write(self.options['ip'].strip())

    #Generate wrapper for boinc cmd
    base_cmd = [cmdbin, '--host', str(self.options['rpc-port']),
                      '--passwd', self.options['passwd'].strip()]
    cc_cmd = ''
    if self.options['cconfig'].strip() != '':
      config_dest = os.path.join(installdir, 'cc_config.xml')
      file = open(config_dest, 'w')
      file.write(open(self.options['cconfig'].strip(), 'r').read())
      file.close()
      cc_cmd = '--read_cc_config'
    cmd = self.createPythonScript(cmd_wrapper,
        '%s.configure.runCmd' % __name__,
        dict(base_cmd=base_cmd, cc_cmd=cc_cmd, installdir=installdir,
        project_url=url, key=key)
    )
    path_list.append(cmd)

    #Generate BOINC client wrapper
    boinc = self.createPythonScript(boinc_wrapper,
            'slapos.recipe.librecipe.execute.execute',
            [boincbin, '--allow_multiple_clients', '--gui_rpc_port',
              str(self.options['rpc-port']), '--allow_remote_gui_rpc',
              '--dir', installdir, '--redirectio', '--check_all_logins']
    )
    path_list.append(boinc)

    return path_list
