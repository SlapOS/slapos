##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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

class Recipe(GenericBaseRecipe):

  def _options(self, options):
    options['password'] = self.generatePassword()
    if 'test-database' in options:
      options['test-password'] = self.generatePassword()
    options.setdefault('parallel-test-database-amount', '0')
    for x in xrange(int(options['parallel-test-database-amount'])):
      options['test-password-%s' % x] = self.generatePassword()

  def install(self):
    path_list = []

    template_filename = self.getTemplateFilename('my.cnf.in')

    mysql_binary = self.options['mysql-binary']
    socket = self.options['socket']

    if 'ip' in self.options:
      networking = 'port = %s\nbind-address = %s' % (
        self.options['port'],
        self.options['ip'],
      )
    else:
      networking = 'skip-networking'

    log_bin = self.options.get('binlog-path', '')
    if log_bin:
      log_bin = 'log_bin = %s' % log_bin
    expire_logs_days = self.options.get('binlog-expire-days')
    if expire_logs_days > 0:
      expire_logs_days = 'expire_logs_days = %s' % expire_logs_days
    else:
      expire_logs_days = ''

    mysql_conf_file = self.createFile(
      self.options['conf-file'],
      self.substituteTemplate(template_filename, {
        'networking': networking,
        'data_directory': self.options['data-directory'],
        'pid_file': self.options['pid-file'],
        'socket': self.options['socket'],
        'error_log': self.options['error-log'],
        'slow_query_log': self.options['slow-query-log'],
        'log_bin': log_bin,
        'expire_logs_days': expire_logs_days,
      })
    )
    path_list.append(mysql_conf_file)

    mysql_script_list = []

    # user defined functions
    udf_registration = ""
    mroonga = self.options.get('mroonga', 'ha_mroonga.so')
    if mroonga:
      udf_registration += "CREATE FUNCTION last_insert_grn_id RETURNS " \
        "INTEGER SONAME '" + mroonga + "';\n"
      udf_registration += "CREATE FUNCTION mroonga_snippet RETURNS " \
        "STRING SONAME '" + mroonga + "';\n"
      udf_registration += "CREATE FUNCTION mroonga_command RETURNS " \
        "STRING SONAME '" + mroonga + "';\n"
    mysql_script_list.append(self.substituteTemplate(
      self.getTemplateFilename('mysql-init-function.sql.in'),
      {
        'udf_registration': udf_registration,
      }
    ))
    # real database
    mysql_script_list.append(self.substituteTemplate(
      self.getTemplateFilename('initmysql.sql.in'),
      {
        'mysql_database': self.options['database'],
        'mysql_user': self.options['user'],
        'mysql_password': self.options['password']
      }
    ))
    # default test database
    if 'test-database' in self.options:
      mysql_script_list.append(self.substituteTemplate(
        self.getTemplateFilename('initmysql.sql.in'),
        {
          'mysql_database': self.options['test-database'],
          'mysql_user': self.options['test-user'],
          'mysql_password': self.options['test-password']
        }
      ))
    # parallel test databases
    for x in xrange(int(self.options['parallel-test-database-amount'])):
      mysql_script_list.append(self.substituteTemplate(
        self.getTemplateFilename('initmysql.sql.in'),
        {
          'mysql_database': self.options['mysql-test-database-base'] + '_%s' % x,
          'mysql_user': self.options['mysql-test-user-base'] + '_%s' % x,
          'mysql_password': self.options['test-password-%s' % x]
        }
      ))
    mysql_script_list.append('EXIT')
    mysql_script = '\n'.join(mysql_script_list)

    mysql_upgrade_binary = self.options['mysql-upgrade-binary']
    mysql_update = self.createPythonScript(
      self.options['update-wrapper'],
      '%s.mysql.updateMysql' % __name__,
      [dict(
        mysql_script=mysql_script,
        mysql_binary=mysql_binary,
        mysql_upgrade_binary=mysql_upgrade_binary,
        socket=socket,
      )]
    )
    path_list.append(mysql_update)

    mysqld = self.createPythonScript(
      self.options['wrapper'],
      '%s.mysql.runMysql' % __name__,
      [dict(
        mysql_base_directory=self.options['mysql-base-directory'],
        mysql_install_binary=self.options['mysql-install-binary'],
        mysqld_binary=self.options['mysqld-binary'],
        data_directory=self.options['data-directory'],
        mysql_binary=mysql_binary,
        socket=socket,
        configuration_file=mysql_conf_file,
       )]
    )
    path_list.append(mysqld)
    environment = dict(PATH='%s' % self.options['bin-directory'])
    # TODO: move to a separate recipe (ack'ed by Cedric)
    if 'backup-script' in self.options:
      # backup configuration
      full_backup = self.options['full-backup-directory']
      incremental_backup = self.options['incremental-backup-directory']
      innobackupex_argument_list = [self.options['perl-binary'],
          self.options['innobackupex-binary'],
          '--defaults-file=%s' % mysql_conf_file,
          '--socket=%s' % socket.strip(), '--user=root',
          '--ibbackup=%s'% self.options['xtrabackup-binary']]
      innobackupex_incremental = self.createPythonScript(self.options['innobackupex-incremental'], 'slapos.recipe.librecipe.execute.executee', [innobackupex_argument_list + ['--incremental'], environment])
      path_list.append(innobackupex_incremental)
      innobackupex_full = self.createPythonScript(self.options['innobackupex-full'], 'slapos.recipe.librecipe.execute.executee', [innobackupex_argument_list, environment])
      path_list.append(innobackupex_full)
      backup_controller = self.createPythonScript(self.options['backup-script'], __name__ + '.innobackupex.controller', [innobackupex_incremental, innobackupex_full, full_backup, incremental_backup])
      path_list.append(backup_controller)
    # TODO: move to a separate recipe (ack'ed by Cedric)
    # percona toolkit (formerly known as maatkit) installation
    for pt_script_name in (
        'pt-align',
        'pt-archiver',
        'pt-config-diff',
        'pt-deadlock-logger',
        'pt-diskstats',
        'pt-duplicate-key-checker',
        'pt-fifo-split',
        'pt-find',
        'pt-fingerprint',
        'pt-fk-error-logger',
        'pt-heartbeat',
        'pt-index-usage',
        'pt-ioprofile',
        'pt-kill',
        'pt-mext',
        'pt-mysql-summary',
        'pt-online-schema-change',
        'pt-pmp',
        'pt-query-digest',
        'pt-show-grants',
        'pt-sift',
        'pt-slave-delay',
        'pt-slave-find',
        'pt-slave-restart',
        'pt-stalk',
        'pt-summary',
        'pt-table-checksum',
        'pt-table-sync',
        'pt-table-usage',
        'pt-upgrade',
        'pt-variable-advisor',
        'pt-visual-explain',
        ):
      option_name = pt_script_name + '-binary'
      if option_name not in self.options:
        continue
      pt_argument_list = [self.options['perl-binary'],
          self.options[option_name],
          '--defaults-file=%s' % mysql_conf_file,
          '--socket=%s' % socket.strip(), '--user=root',
          ]
      pt_exe = self.createPythonScript(os.path.join(self.options['bin-directory'], pt_script_name), 'slapos.recipe.librecipe.execute.executee', [pt_argument_list, environment])
      path_list.append(pt_exe)

    return path_list

class WrapUpdateMySQL(GenericBaseRecipe):
  def install(self):
    return [
      self.createPythonScript(
        self.options['output'],
        __name__ + '.mysql.updateMysql',
        [{
          'mysql_upgrade_binary': self.options['binary'],
          'mysql_binary': self.options['mysql'],
          'mysql_script_file': self.options['init-script'],
        }]
      ),
    ]

class WrapMySQLd(GenericBaseRecipe):
  def install(self):
    return [
      self.createPythonScript(
        self.options['output'],
        __name__ + '.mysql.runMysql',
        [{
          'mysqld_binary': self.options['binary'],
          'configuration_file': self.options['configuration-file'],
          'data_directory': self.options['data-directory'],
          'mysql_install_binary': self.options['mysql-install-binary'],
          'mysql_base_directory': self.options['mysql-base-directory'],
        }]
      ),
    ]
