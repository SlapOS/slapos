##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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
from binascii import b2a_uu as uuencode
import binascii
import os
import sys

class Recipe(GenericBaseRecipe):
  """
  nginx instance configuration.
  """

  def install(self):
    path_list = []
    config = dict(
      nb_workers = self.options["nb_workers"],
      path_pid = self.options["pid-file"],
      path_log = self.options["log-file"],
      path_access_log = self.options["access-log"],
      path_error_log = self.options["error-log"],
      root = self.options["nginx-root"],
      ip = self.options["ip"],
      port = self.options["port"],
      tmp = self.options["tmp-dir"],
      index_page_id = self.options.get("index-page-id", "index.php"),
      php_cgi_address = self.options["php-cgi-address"]
    )
    
    # Configs
    self.createFile(
      self.options['config_file'],
      self.substituteTemplate(self.getTemplateFilename('nginx_conf.in'), config))

        # Configs
    self.createFile(
      self.options['mime_path'],
      self.substituteTemplate(self.getTemplateFilename('mime_types.in'), config))

    wrapper = self.createPythonScript(self.options['wrapper'],
        'slapos.recipe.librecipe.execute.execute',
        [self.options['nginx-binary'], '-c', self.options["config_file"],
         ]
    )
    path_list.append(wrapper)

    # Install php.ini
    php_ini = self.createFile(os.path.join(self.options['php-ini-dir'],
                                           'php.ini'),
      self.substituteTemplate(self.getTemplateFilename('php.ini.in'),
        dict(tmp_directory=self.options['tmp-dir']))
    )
    path_list.append(php_ini)

    wrapper = self.createPythonScript(self.options['php-cgi-wrapper'],
        'slapos.recipe.librecipe.execute.execute',
        [self.options['php-cgi-binary'], '-b', self.options['php-cgi-address'],
         ]
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

    # Generate application configuration file
    if self.options.get('template'):
      application_conf = dict(mysql_database=self.options['mysql-database'],
                              mysql_user=self.options['mysql-username'],
                              mysql_password=self.options['mysql-password'],
                              mysql_host='%s:%s' % (self.options['mysql-host'],
                                                    self.options['mysql-port']),
                              secret_key=secret_key,
                             )

      directory, file_ = os.path.split(self.options['configuration'])

      path = self.options['nginx-root']
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
    
    return path_list
