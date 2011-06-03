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
import pkg_resources
import sys
import zc.buildout

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    #self.requirements, self.ws = self.egg.working_set([__name__])
    # XXX-CEDRIC ARRRRRR IT TOOK ME 3 HOURS TO FIND THAT
    # self.egg.working_set([__name__])
    # DOES NOT WORK : __name__ IS "slapos.recipe.mysql" BUT THIS EGG
    # DOES NOT EXIST SO BUILDOUT FAILS MISERABLY WHILE FINDING A DISTRIBUTION
    # "slapos.recipe.mysql". SLAPOS.COOKBOOK EXISTS. UGLY WORKAROUND.
    self.requirements, self.ws = self.egg.working_set(['slapos.cookbook'])
    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    
    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)

    self.linkBinary()
    self.setConnectionDict(dict(
      ip = mysql_conf['ip'],
      port = mysql_conf['tcp_port'],
      database = mysql_conf['mysql_database'],
      user = mysql_conf['mysql_user'],
      password = mysql_conf['mysql_password'],
    ))
    return self.path_list

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)

  def installCrond(self):
    timestamps = self.createDataDirectory('cronstamps')
    cron_output = os.path.join(self.log_directory, 'cron-output')
    self._createDirectory(cron_output)
    catcher = zc.buildout.easy_install.scripts([('catchcron',
      __name__ + '.catdatefile', 'catdatefile')], self.ws, sys.executable,
      self.bin_directory, arguments=[cron_output])[0]
    self.path_list.append(catcher)
    cron_d = os.path.join(self.etc_directory, 'cron.d')
    crontabs = os.path.join(self.etc_directory, 'crontabs')
    self._createDirectory(cron_d)
    self._createDirectory(crontabs)
    wrapper = zc.buildout.easy_install.scripts([('crond',
      __name__ + '.execute', 'execute')], self.ws, sys.executable,
      self.wrapper_directory, arguments=[
        self.options['dcrond_binary'].strip(), '-s', cron_d, '-c', crontabs,
        '-t', timestamps, '-f', '-l', '5', '-M', catcher]
      )[0]
    self.path_list.append(wrapper)
    return cron_d
  
  def installLogrotate(self):
    """Installs logortate main configuration file and registers its to cron"""
    logrotate_d = os.path.abspath(os.path.join(self.etc_directory,
      'logrotate.d'))
    self._createDirectory(logrotate_d)
    logrotate_backup = self.createBackupDirectory('logrotate')
    logrotate_conf = self.createConfigurationFile("logrotate.conf",
        "include %s" % logrotate_d)
    logrotate_cron = os.path.join(self.cron_d, 'logrotate')
    state_file = os.path.join(self.data_root_directory, 'logrotate.status')
    open(logrotate_cron, 'w').write('0 0 * * * %s -s %s %s' %
        (self.options['logrotate_binary'], state_file, logrotate_conf))
    self.path_list.extend([logrotate_d, logrotate_conf, logrotate_cron])
    return logrotate_d, logrotate_backup

  def registerLogRotation(self, name, log_file_list, postrotate_script):
    """Register new log rotation requirement"""
    open(os.path.join(self.logrotate_d, name), 'w').write(
        self.substituteTemplate(self.getTemplateFilename(
          'logrotate_entry.in'),
          dict(file_list=' '.join(['"'+q+'"' for q in log_file_list]),
            postrotate=postrotate_script, olddir=self.logrotate_backup)))
  
  def installMysqlServer(self, ip, port, database='database', user='user',
      template_filename=None, mysql_conf=None):
    if mysql_conf is None:
      mysql_conf = {}
    backup_directory = self.createBackupDirectory('mysql')
    if template_filename is None:
      template_filename = self.getTemplateFilename('my.cnf.in')
    error_log = os.path.join(self.log_directory, 'mysqld.log')
    slow_query_log = os.path.join(self.log_directory, 'mysql-slow.log')
    mysql_conf.update(
        ip=ip,
        data_directory=os.path.join(self.data_root_directory,
          'mysql'),
        tcp_port=port,
        pid_file=os.path.join(self.run_directory, 'mysqld.pid'),
        socket=os.path.join(self.run_directory, 'mysqld.sock'),
        error_log=error_log,
        slow_query_log=slow_query_log,
        mysql_database=database,
        mysql_user=user,
        mysql_password=self.generatePassword(),
    )
    self.registerLogRotation('mysql', [error_log, slow_query_log],
        '%(mysql_binary)s --no-defaults -B --user=root '
        '--socket=%(mysql_socket)s -e "FLUSH LOGS"' % dict(
          mysql_binary=self.options['mysql_binary'],
          mysql_socket=mysql_conf['socket']))
    self._createDirectory(mysql_conf['data_directory'])

    mysql_conf_path = self.createConfigurationFile("my.cnf",
        self.substituteTemplate(template_filename,
          mysql_conf))

    mysql_script_list = []
    for x_database, x_user, x_password in \
          [(mysql_conf['mysql_database'],
            mysql_conf['mysql_user'],
            mysql_conf['mysql_password']),
          ]:
      mysql_script_list.append(pkg_resources.resource_string(__name__,
                     'template/initmysql.sql.in') % {
                        'mysql_database': x_database,
                        'mysql_user': x_user,
                        'mysql_password': x_password})
    mysql_script_list.append('EXIT')
    mysql_script = '\n'.join(mysql_script_list)
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

    # backup configuration
    backup_directory = self.createBackupDirectory('mysql')
    full_backup = os.path.join(backup_directory, 'full')
    incremental_backup = os.path.join(backup_directory, 'incremental')
    self._createDirectory(full_backup)
    self._createDirectory(incremental_backup)
    innobackupex_argument_list = [self.options['perl_binary'],
        self.options['innobackupex_binary'],
        '--defaults-file=%s' % mysql_conf_path,
        '--socket=%s' %mysql_conf['socket'].strip(), '--user=root']
    environment = dict(PATH='%s' % self.bin_directory)
    innobackupex_incremental = zc.buildout.easy_install.scripts([(
      'innobackupex_incremental', __name__ + '.execute', 'executee')],
      self.ws, sys.executable, self.bin_directory, arguments=[
        innobackupex_argument_list + ['--incremental'],
        environment])[0]
    self.path_list.append(innobackupex_incremental)
    innobackupex_full = zc.buildout.easy_install.scripts([('innobackupex_full',
      __name__ + '.execute', 'executee')], self.ws,
      sys.executable, self.bin_directory, arguments=[
        innobackupex_argument_list,
        environment])[0]
    self.path_list.append(innobackupex_full)
    backup_controller = zc.buildout.easy_install.scripts([
      ('innobackupex_controller', __name__ + '.innobackupex', 'controller')],
      self.ws, sys.executable, self.bin_directory,
      arguments=[innobackupex_incremental, innobackupex_full, full_backup,
        incremental_backup])[0]
    self.path_list.append(backup_controller)
    mysql_backup_cron = os.path.join(self.cron_d, 'mysql_backup')
    open(mysql_backup_cron, 'w').write('0 0 * * * ' + backup_controller)
    self.path_list.append(mysql_backup_cron)
    # The return could be more explicit database, user ...
    return mysql_conf
