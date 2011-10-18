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
from slapos.recipe.librecipe import GenericSlapRecipe
import os
import json
import pkg_resources

ZOPE_PORT_BASE = 12000
ZEO_PORT_BASE = 15000
HAPROXY_PORT_BASE = 11000
APACHE_PORT_BASE = 10000

class Recipe(GenericSlapRecipe):
  def _options(self, options):
    self.dirname = os.path.join(self.buildout['buildout']['parts-directory'],
      self.name)
    options['output'] = os.path.join(self.dirname, self.name)

  def _generateRealTemplate(self):
    # always one distribution node
    # always one admin node
    current_zeo_port = ZEO_PORT_BASE
    current_zope_port = ZOPE_PORT_BASE
    json_data = json.loads(self.parameter_dict['json'])
    site_id = str(json_data['site-id'])
    # prepare zeo
    output = ''
    part_list = []
    for zeo_id, zeo_configuration in json_data['zeo'].iteritems():
      current_zeo_port += 1
      output += pkg_resources.resource_string(__name__,
        'template/snippet-zeo.cfg') % dict(
        zeo_id=zeo_id,
        zeo_port=current_zeo_port,
        storage_list=' '.join([str(q['zodb']) for q in zeo_configuration])
      ) + '\n'
      part_list.extend([
        "zeo-instance-%s" % zeo_id,
        "logrotate-entry-zeo-%s" % zeo_id
      ])
    prepend = pkg_resources.resource_string(__name__,
        'template/instance.cfg') % dict(
        part_list='  \n'.join(['  '+q for q in part_list]))
    output = prepend + output
    print output
    raise NotImplementedError

  def _install(self):
    if not os.path.exists(self.dirname):
      os.mkdir(self.dirname)
    if not "json" in self.parameter_dict:
      # no json transimtted, nothing to do
      with open(options['output'], 'w') as f:
        f.write("[buildout]\nparts =\n")
    else:
      self._generateRealTemplate()
    return [self.dirname]
