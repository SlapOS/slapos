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

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def install(self):
    path_list = []

    # Install apache
    apache_config = dict(
      pid_file=self.options['pid-file'],
      lock_file=self.options['lock-file'],
      ip=self.options['ip'],
      port=self.options['port'],
      error_log=self.options['error-log'],
      access_log=self.options['access-log'],
      backend_url=self.options['url'],
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
                                     '-DFOREGROUND',
                                     ])

    path_list.append(wrapper)

    subprocess.call([
                        self.options['httpd-binary'],
                        '-f',
                        self.options['httpd-conf'],
                        '-k',
                        'graceful',
                    ])

    return path_list

