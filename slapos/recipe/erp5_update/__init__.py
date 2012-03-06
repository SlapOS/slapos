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
import urlparse
from slapos.recipe.librecipe import GenericSlapRecipe

class Recipe(GenericSlapRecipe):
  def _install(self):
    conversion_server = None
    if 'cloudooo-url' in self.options and self.options['cloudooo-url']:
      parsed = urlparse.urlparse(self.options['cloudooo-url'])
      conversion_server = "%s:%s" % (parsed.hostname, parsed.port)
    memcached = None
    if 'memcached-url' in self.options and self.options['memcached-url']:
      parsed = urlparse.urlparse(self.options['memcached-url'])
      memcached = "%s:%s" % (parsed.hostname, parsed.port)
    kumofs = None
    if 'kumofs-url' in self.options and self.options['kumofs-url']:
      parsed = urlparse.urlparse(self.options['kumofs-url'])
      kumofs = "%s:%s" % (parsed.hostname, parsed.port)

    parsed = urlparse.urlparse(self.options['mysql-url'])
    mysql_connection_string = "%(database)s@%(hostname)s:%(port)s "\
        "%(username)s %(password)s" % dict(
      database=parsed.path.split('/')[1],
      hostname=parsed.hostname,
      port=parsed.port,
      username=parsed.username,
      password=parsed.password
    )

    parsed = urlparse.urlparse(self.options['url'])
    zope_user = parsed.username
    zope_password = parsed.password
    zope_host = '%s:%s' % (parsed.hostname, parsed.port)
    bt5_list = []
    if len(self.parameter_dict.get("bt5_list", "").strip()):
      bt5_list = self.parameter_dict["bt5_list"].split()
    elif self.parameter_dict.get("flavour", "default") == 'configurator':
      bt5_list = self.options['configurator-bt5-list'].split()
    bt5_repository_list = self.parameter_dict.get("bt5_repository_list",
      "").split() or self.options['bt5-repository-list'].split()

    script = self.createPythonScript(self.options['update-wrapper'],
      __name__+'.erp5.updateERP5', [
        self.options['site-id'], mysql_connection_string,
        [zope_user, zope_password, zope_host],
        memcached, conversion_server, kumofs, bt5_list, bt5_repository_list,
        self.options['cadir-path'], self.options['openssl-binary']])
    return [script]
