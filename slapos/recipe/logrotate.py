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
import os

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def _options(self, options):
    if 'name' not in options:
      options['name'] = self.name

  def install(self):
    path_list = []

    logrotate_backup = self.options['backup']
    logrotate_d = self.options['logrotate-entries']
    logrotate_conf_file = self.options['conf']

    logrotate_conf = []
    logrotate_conf.append("include %s" % logrotate_d)
    logrotate_conf.append("olddir %s" % logrotate_backup)
    logrotate_conf.append("dateext")

    frequency = 'daily'
    if 'frequency' in self.options:
      frequency = self.options['frequency']
    logrotate_conf.append(frequency)

    num_rotate = 30
    if 'num-rotate' in self.options:
      num_rotate = self.options['num-rotate']
    logrotate_conf.append("rotate %s" % num_rotate)

    logrotate_conf.append("compress")
    logrotate_conf.append("compresscmd %s" % self.options['gzip-binary'])
    logrotate_conf.append("compressoptions -9")
    logrotate_conf.append("uncompresscmd %s" % self.options['gunzip-binary'])

    logrotate_conf_file = self.createFile(logrotate_conf_file, '\n'.join(logrotate_conf))
    logrotate_conf.append(logrotate_conf_file)

    state_file = self.options['state-file']

    logrotate = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.exceute.execute',
      [self.options['logrotate-binary'], '-s', state_file, logrotate_conf_file, ]
    )
    path_list.append(logrotate)

    return path_list

class Part(GenericBaseRecipe):

  def _options(self, options):
    if 'name' not in options:
      options['name'] = self.name

  def install(self):

    logrotate_d = self.options['logrotate-entries']

    part_path = os.path.join(logrotate_d, self.options['name'])

    conf = []

    if 'frequency' in self.options:
      conf.append(self.options['frequency'])
    if 'num-rotate' in self.options:
      conf.append('rotate %s' % self.options['num-rotate'])

    if 'post' in self.options:
      conf.append("postrotate\n%s\nendscript" % self.options['post'])
    if 'pre' in self.options:
      conf.append("prerotate\n%s\nendscript" % self.options['pre'])

    if self.optionIsTrue('sharedscripts', False):
      conf.append("sharedscripts")

    if self.optionIsTrue('notifempty', False):
      conf.append('notifempty')

    if self.optionIsTrue('create', True):
      conf.append('create')

    log = self.options['log']

    self.createFile(os.path.join(logrotate_d, self.options['name']),
                    "%(logfiles)s {\n%(conf)s\n}" % {
                      'logfiles': log,
                      'conf': '\n'.join(conf),
                    }
                   )

    return [part_path]
