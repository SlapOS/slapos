##############################################################################
#
# Copyright (c) 2012-2014 Vifib SARL and Contributors. All Rights Reserved.
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
import sys
import urlparse

class Recipe(GenericBaseRecipe):
  """
  Instanciate ERP5 in Zope
  """

  def install(self):
    mysql = urlparse.urlsplit(self.options['mysql-url'])
    zope = urlparse.urlsplit(self.options['zope-url'])
    # Note: raises when there is more than a single element in path, as it's
    # not supported by manage_addERP5Site anyway.
    _, zope_path = zope.path.split('/')
    return [self.createExecutable(
      self.options['runner-path'],
      self.substituteTemplate(
        self.getTemplateFilename('erp5_bootstrap.in'),
        {
          'python_path': sys.executable,
          'base_url': urlparse.urlunsplit((zope.scheme, zope.netloc, '', '', '')),
          'site_id': zope_path,
          'sql_connection_string': '%(database)s@%(hostname)s:%(port)s %(username)s %(password)s' % {
            'database': mysql.path.split('/')[1],
            'hostname': mysql.hostname,
            'port': mysql.port,
            'username': mysql.username,
            'password': mysql.password
          },
        },
    ))]
