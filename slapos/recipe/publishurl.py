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
import zc.buildout

from slapos.recipe.librecipe import GenericSlapRecipe

class Recipe(GenericSlapRecipe):

  def _options(self, options):

    self.useparts = True

    if 'url' in options:
      self.useparts = False
      self.url = options['url']
    else:
      self.urlparts = {}

      if 'scheme' not in options:
        raise zc.buildout.UserError("No scheme specified.")
      else:
        self.urlparts.update(scheme=options['scheme'])
      if 'host' not in options:
        raise zc.buildout.UserError("No host specified.")
      else:
        self.urlparts.update(host=options['host'])

  def _install(self):

    if self.useparts:
      for option in ['path', 'params', 'query', 'fragment', 'port']:
        if option in self.options:
          self.urlparts[option] = self.options[option]

      if 'username' in self.options:
        self.urlparts.update(auth=(self.options['username'],))
        if 'password' in self.options:
          self.urlparts.update(auth=(self.options['username'],
                                     self.options['password']))

      self.setConnectionUrl(**self.urlparts)
    else:
      self.setConnectionDict(dict(url=self.url))

    return []
