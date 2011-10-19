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

ZOPE_PORT_BASE = 12000
ZEO_PORT_BASE = 15000
HAPROXY_PORT_BASE = 11000
APACHE_PORT_BASE = 10000

class Recipe(GenericSlapRecipe):
  def _options(self, options):
    self.dirname = os.path.join(self.buildout['buildout']['parts-directory'],
      self.name)
    options['output'] = os.path.join(self.dirname, self.name + '.cfg')

  def _generateRealTemplate(self):
    current_zeo_port = ZEO_PORT_BASE
    current_zope_port = ZOPE_PORT_BASE
    json_data = json.loads(self.parameter_dict['json'])
    site_id = str(json_data['site-id'])
    # prepare zeo
    output = ''
    part_list = []
    zope_dict = {}
    zope_connection_dict = {}
    snippet_zeo = open(self.options['snippet-zeo']).read()
    for zeo_id, zeo_configuration in json_data['zeo'].iteritems():
      current_zeo_port += 1
      output += snippet_zeo % dict(
        zeo_id=zeo_id,
        zeo_port=current_zeo_port,
        storage_list=' '.join([str(q['zodb']) for q in zeo_configuration])
      ) + '\n'
      part_list.extend([
        "zeo-instance-%s" % zeo_id,
        "logrotate-entry-zeo-%s" % zeo_id
      ])
      for zeo_slave in zeo_configuration:
        zope_connection_dict[zeo_slave['zodb']] = {
          'zope-cache-size': zeo_slave['zope-cache-size'],
          'zeo-cache-size': zeo_slave['zeo-cache-size'],
          'mount-point': zeo_slave['mount-point'] % {'site-id': site_id},
          'storage': zeo_slave['zodb'],
          'name': zeo_slave['zodb'],
          'server': '${zeo-instance-%(zeo-id)s:ip}:${zeo-instance-%(zeo-id)s:port}' % {'zeo-id': zeo_id}
      }

    zeo_connection_list = []
    a = zeo_connection_list.append
    for k, v in zope_connection_dict.iteritems():
      a('  zeo-cache-size=%(zeo-cache-size)s zope-cache-size=%(zope-cache-size)s server=%(server)s mount-point=%(mount-point)s ' % v)
    zeo_connection_string = '\n'.join(zeo_connection_list)
    zope_dict.update(
      timezone=json_data['timezone'],
      zeo_connection_string=zeo_connection_string
    )
    # always one distribution node
    current_zope_port += 1
    snippet_zope = open(self.options['snippet-zope']).read()
    zope_id = 'zope-distribution'
    part_list.append(zope_id)
    output += snippet_zope % dict(zope_thread_amount=1, zope_id=zope_id, zope_port=current_zope_port,
      **zope_dict)
    # always one admin node
    current_zope_port += 1
    zope_id = 'zope-admin'
    part_list.append(zope_id)
    output += snippet_zope % dict(zope_thread_amount=1, zope_id=zope_id, zope_port=current_zope_port,
      **zope_dict)
    # handle activity key
    for q in range(1, json_data['activity']['zopecount'] + 1):
      current_zope_port += 1
      part_name = 'zope-activity-%s' % q
      part_list.append(part_name)
      output += snippet_zope % dict(zope_thread_amount=1, zope_id=part_name, zope_port=current_zope_port,
        **zope_dict)
    # handle backend key
    for backend_type, backend_configuration in json_data['backend'].iteritems():
      for q in range(1, backend_configuration['zopecount'] + 1):
        current_zope_port += 1
        part_name = 'zope-%s-%s' % (backend_type, q)
        part_list.append(part_name)
        output += snippet_zope % dict(zope_thread_amount=backend_configuration['thread-amount'], zope_id=part_name, zope_port=current_zope_port, **zope_dict)
    prepend = open(self.options['snippet-master']).read() % dict(
        part_list='  \n'.join(['  '+q for q in part_list]))
    output = prepend + output
    with open(self.options['output'], 'w') as f:
      f.write(output)

  def _install(self):
    if not os.path.exists(self.dirname):
      os.mkdir(self.dirname)
    if not "json" in self.parameter_dict:
      # no json transimtted, nothing to do
      with open(self.options['output'], 'w') as f:
        f.write("[buildout]\nparts =\n")
    else:
      self._generateRealTemplate()
    return [self.dirname]
