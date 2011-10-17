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

class Recipe(GenericBaseRecipe):

  def _options(self, options):
    options['password'] = self.generatePassword()

  def install(self):
    path_list = []

    template_filename = self.getTemplateFilename('my.cnf.in')

    mysql_conf = dict(
        ip=self.options['ip'],
        data_directory=self.options['data-directory'],
        tcp_port=self.options['port'],
        pid_file=self.options['pid-file'],
        socket=self.options['socket'],
        error_log=self.options['error-log'],
        slow_query_log=self.options['slow-query-log'],
        mysql_database=self.options['database'],
        mysql_user=self.options['user'],
        mysql_password=self.options['password'],
    )

    mysql_binary = self.options['mysql-binary']
    socket = self.options['socket'],
    post_rotate = self.createPythonScript(
      self.options['logrotate-post'],
      'slapos.recipe.librecipe.execute.execute',
      [mysql_binary, '--no-defaults', '-B', '--socket=%s' % socket, '-e',
       'FLUSH LOGS']
    )
    path_list.append(post_rotate)

    mysql_conf_file = self.createFile(
      self.options['conf-file'],
      self.substituteTemplate(template_filename, mysql_conf)
    )
    path_list.append(mysql_conf_file)

    mysql_script_list = []

    init_script = self.substituteTemplate(
      self.getTemplateFilename('initmysql.sql.in'),
      {
        'mysql_database': mysql_conf['mysql_database'],
        'mysql_user': mysql_conf['mysql_user'],
        'mysql_password': mysql_conf['mysql_password']
      }
    )
    mysql_script_list.append(init_script)
    mysql_script_list.append('EXIT')
    mysql_script = '\n'.join(mysql_script_list)

    mysql_upgrade_binary = self.options['mysql-upgrade-binary']
    mysql_update = self.createPythonScript(
      self.options['update-wrapper'],
      '%s.mysql.updateMysql' % __name__,
      dict(
        mysql_script=mysql_script,
        mysql_binary=mysql_binary,
        mysql_upgrade_binary=mysql_upgrade_binary,
        socket=socket,
      )
    )
    path_list.append(mysql_update)

    mysqld_binary = self.options['mysqld-binary']
    mysqld = self.createPythonScript(
      self.options['wrapper'],
      '%s.mysql.runMysql' % __name__,
      dict(
        mysql_install_binary=self.options['mysql-install-binary'],
        mysqld_binary=mysqld_binary,
        data_directory=mysql_conf['data_directory'],
        mysql_binary=mysql_binary,
        socket=socket,
        configuration_file=mysql_conf_file,
       )
    )
    path_list.append(mysqld)

    # backup configuration
    mysqldump_binary = self.options['mysqldump-binary']
    backup_directory = self.options['backup-directory']
    pending_backup_dir = self.options['backup-pending-directory']
    dump_filename = self.options['dumpname']

    mysqldump_cmd = [mysqldump_binary,
                     mysql_conf['mysql_database'],
                     '-u', 'root',
                     '-S', mysql_conf['socket'].strip(),
                     '--single-transaction', '--opt',
                    ]
    dump_file = os.path.join(backup_directory, dump_filename)
    tmpdump_file = os.path.join(pending_backup_dir, dump_filename)
    backup_script = self.createPythonScript(
      self.options['backup-script'],
      '%s.backup.do_backup' % __name__,
      {
        'mysqldump': mysqldump_cmd,
        'gzip': self.options['gzip-binary'],
        'tmpdump': tmpdump_file,
        'dumpfile': dump_file,
      },
    )
    path_list.append(backup_script)

    # Recovering backup
    if self.optionIsTrue('recovering', default=False):
      recovering_script = self.createPythonScript(
        self.options['recovering-wrapper'],
        '%s.recover.import_remote_dump' % __name__,
        {
          'lock_file': os.path.join(self.work_directory,
                                    'import_done'),
          'database': mysql_conf['mysql_database'],
          'mysql_binary': self.options['mysql-binary'],
          'mysql_socket': mysql_conf['socket'],
          'duplicity_binary': self.options['duplicity-binary'],
          'remote_backup': self.parameter_dict['remote-backup'],
          'local_directory': self.mysql_backup_directory,
          'dump_name': dump_filename,
          'zcat_binary': self.options['zcat-binary'],
        }
      )
      path_list.append(recovering_script)


    return path_list
