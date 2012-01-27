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
import multiprocessing

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def install(self):
    path_list = []

    # Get uniq peers
    peers_list = [p for p in self.options['peers'].split('\n') if p]
    peers_list = list(set(peers_list))

    config_file = self.createFile(
      self.options['config-file'],
      self.substituteTemplate(
        self.getTemplateFilename('config.in'),
        {
          'peers': peers_list,
          'database': self.options['database'],
          'equeue_socket': self.options['equeue-socket'],
          'callbacks_directory': self.options['callbacks-directory'],
          'partition_id': self.options['partition-id'],
          'computer_id': self.options['computer-id'],
          'agent_type': self.options['type'],
        }
      ),
    )
    path_list.append(config_file)

    bind_address = self.options['host']
    if ':' in bind_address:
      bind_address = '[%s]' % bind_address
    bind_address = '%s:%s' % (bind_address, self.options['port'])

    wrapper = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.executee',
      [ # Command line
        [
          self.options['gunicorn'],
          '-b', bind_address,
          '-w', '%d' % (multiprocessing.cpu_count() * 2 + 1),
          '-k', 'gevent',
          'slapos.wordpress.ia.http:app',
        ],
        # Environment
        dict(CONFIG=config_file),
      ]
    )
    path_list.append(wrapper)

    return path_list
