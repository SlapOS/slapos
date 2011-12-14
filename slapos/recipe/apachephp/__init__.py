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
import shutil
import os
import signal
from binascii import b2a_uu as uuencode

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def install(self):
    path_list = []

    # Copy application
    shutil.rmtree(self.options['htdocs'])
    shutil.copytree(self.options['source'],
                    self.options['htdocs'])

    # Install php.ini
    php_ini = self.createFile(os.path.join(self.options['php-ini-dir'],
                                           'php.ini'),
      self.substituteTemplate(self.getTemplateFilename('php.ini.in'),
        dict(tmp_directory=self.options['tmp-dir']))
    )
    path_list.append(php_ini)

    # Install apache
    apache_config = dict(
      pid_file=self.options['pid-file'],
      lock_file=self.options['lock-file'],
      ip=self.options['ip'],
      port=self.options['port'],
      error_log=self.options['error-log'],
      access_log=self.options['access-log'],
      document_root=self.options['htdocs'],
      php_ini_dir=self.options['php-ini-dir'],
    )
    httpd_conf = self.createFile(self.options['httpd-conf'],
      self.substituteTemplate(self.getTemplateFilename('apache.in'),
                              apache_config)
    )
    path_list.append(httpd_conf)

    wrapper = self.createPythonScript(self.options['wrapper'],
        'slapos.recipe.librecipe.execute.execute',
        [self.options['httpd-binary'], '-f', self.options['httpd-conf'],
         '-DFOREGROUND']
    )
    path_list.append(wrapper)

    secret_key_filename = os.path.join(self.buildout['buildout']['directory'],
                                       '.php_secret_key')
    if not os.path.exists(secret_key_filename):
      secret_key = uuencode(os.urandom(45)).strip()
      # Remove unsafe characters
      secret_key = secret_key.translate(None, '"\'')
      with open(secret_key_filename, 'w') as secret_key_file:
        secret_key_file.write(secret_key)
    else:
      with open(secret_key_filename, 'r') as secret_key_file:
        secret_key = secret_key_file.read()

    application_conf = dict(mysql_database=self.options['mysql-database'],
                            mysql_user=self.options['mysql-username'],
                            mysql_password=self.options['mysql-password'],
                            mysql_host='%s:%s' % (self.options['mysql-host'],
                                                  self.options['mysql-port']),
                            secret_key=secret_key,
                           )

    directory, file_ = os.path.split(self.options['configuration'])

    path = self.options['htdocs']
    if directory:
      path = os.path.join(path, directory)
      if not os.path.exists(path):
        os.makedirs(path)
      if not os.path.isdir(path):
        raise OSError("Cannot create %r." % path)

    destination = os.path.join(path, file_)
    config = self.createFile(destination,
      self.substituteTemplate(self.options['template'], application_conf))
    path_list.append(config)

    if os.path.exists(self.options['pid-file']):
      # Reload apache configuration
      with open(self.options['pid-file']) as pid_file:
        pid = int(pid_file.read().strip(), 10)
      os.kill(pid, signal.SIGUSR1) # Graceful restart

    return path_list
