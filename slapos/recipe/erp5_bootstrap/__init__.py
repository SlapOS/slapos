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
import os
import sys
import urlparse

class Recipe(GenericBaseRecipe):
  """
  Instanciate ERP5 in Zope
  """

  def install(self):
    parsed = urlparse.urlparse(self.options['mysql-url'])
    mysql_connection_string = "%(database)s@%(hostname)s:%(port)s "\
        "%(username)s %(password)s" % dict(
      database=parsed.path.split('/')[1],
      hostname=parsed.hostname,
      port=parsed.port,
      username=parsed.username,
      password=parsed.password
    )

    zope_parsed = urlparse.urlparse(self.options['zope-url'])

    # Extract zope username/password from url, or get it from options
    if zope_parsed.username:
      zope_username = zope_parsed.username
    else:
      zope_username = self.options['zope-username']
    if zope_parsed.password:
      zope_password = zope_parsed.password
    else:
      zope_password = self.options['zope-password']

    config = dict(
      python_path=sys.executable,
      user=zope_username,
      password=zope_password,
      site_id=zope_parsed.path.split('/')[1],
      host="%s:%s" % (zope_parsed.hostname, zope_parsed.port),
      sql_connection_string=mysql_connection_string,
    )

    # Runners
    runner_path = self.createExecutable(
      self.options['runner-path'],
      self.substituteTemplate(self.getTemplateFilename('erp5_bootstrap.in'),
                              config))

    return [runner_path]
