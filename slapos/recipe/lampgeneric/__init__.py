##############################################################################
#
# Copyright (c) 2013 Vifib SARL and Contributors. All Rights Reserved.
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
import zc.buildout

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  # XXX-Cedric: write docstring

  def install(self):
    path_list = []

    # Download and unpack application if not already existing
    htdocs_location = self.options['htdocs']
    if not (os.path.exists(htdocs_location) and os.listdir(htdocs_location)):
      try:
        os.rmdir(htdocs_location)
      except:
        pass
      self.download(htdocs_location)

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

    wrapper = self.createWrapper(name=self.options['wrapper'],
                                 command=self.options['httpd-binary'],
                                 parameters=[
                                     '-f',
                                     self.options['httpd-conf'],
                                     '-DFOREGROUND'
                                     ])
    path_list.append(wrapper)


    return path_list
