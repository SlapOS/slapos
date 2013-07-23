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
import subprocess
import httplib
import base64
import os
import shutil

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def _options(self, options):
    options['password'] = self.generatePassword()

  def install(self):
    path_list = []

    htpasswd_file = self.options['htpasswd-file']
    # Create or empty the file
    open(htpasswd_file, 'w').close()
    path_list.append(htpasswd_file)

    user = self.options['user']
    password = self.options['password']
    subprocess.check_call([self.options['apache-htpasswd'],
                           '-bc', htpasswd_file,
                           user, password
                          ])

    htdocs_location = self.options['htdocs']
    if not (os.path.exists(htdocs_location) and os.listdir(htdocs_location)):
      try:
        os.rmdir(htdocs_location)
      except:
        pass
      shutil.copytree(self.options['source'], htdocs_location)

    # Install php.ini
    php_ini = self.createFile(os.path.join(self.options['php-ini-dir'],
                                             'php.ini'),
                                self.substituteTemplate(self.getTemplateFilename('php.ini.in'),
                                dict(tmp_directory=self.options['tmp-dir']))
                )
    path_list.append(php_ini)
    
    apache_config = dict(
      pid_file=self.options['pid-file'],
      lock_file=self.options['lock-file'],
      davlock_db=self.options['davdb-lock'],
      ip=self.options['ip'],
      port_webdav=self.options['port_webdav'],
      port_ajax=self.options['port_ajax'],
      error_log=self.options['error-log'],
      access_log=self.options['access-log'],
      document_root=self.options['htdocs'],
      modules_dir=self.options['apache-modules-dir'],
      mime_types=self.options['apache-mime-file'],
      server_root=self.options['root'],
      email_address=self.options['email-address'],
      htpasswd_file=htpasswd_file,
      ssl_certificate=self.options['cert-file'],
      ssl_key=self.options['key-file'],
      php_ini_dir=self.options['php-ini-dir']
    )

    # Create logfiles
    for log in [self.options['error-log'], self.options['access-log']]:
      open(log, 'a').close()

    config_file = self.createFile(self.options['conf-file'],
       self.substituteTemplate(self.getTemplateFilename('httpd.conf.in'),
                               apache_config)
    )
    path_list.append(config_file)

    wrapper = self.createPythonScript(self.options['wrapper'],
      'slapos.recipe.librecipe.execute.execute',
      [self.options['apache-binary'], '-f', config_file, '-DFOREGROUND'])
    path_list.append(wrapper)

    promise = self.createPythonScript(self.options['promise'],
      __name__ + '.promise',
      dict(host=self.options['ip'], port=int(self.options['port_webdav']),
           user=self.options['user'], password=self.options['password'])
                                     )
    path_list.append(promise)

    return path_list

def promise(args):
  host = args['host']
  port = args['port']
  user = args['user']
  password = args['password']

  connection = httplib.HTTPSConnection(host, port)
  auth = base64.b64encode('%s:%s' % (user, password))
  connection.request('OPTIONS', '/',
                     headers=dict(
                       Authorization='Basic %s' % auth,
                     )
                    )
  connection.getresponse()

  return 0
