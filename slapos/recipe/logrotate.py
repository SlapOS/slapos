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

  def install(self):
    logrotate_backup = self.options['backup']
    logrotate_d = self.options['logrotate-entries']
    logrotate_conf_file = self.options['conf']

    logrotate_conf = [
      'daily',
      'dateext',
      'rotate 3650',
      'compress',
      'compresscmd %s' % self.options['gzip-binary'],
      'compressoptions -9',
      'uncompresscmd %s' % self.options['gunzip-binary'],
      'notifempty',
      'sharedscripts',
      'create',
      'include %s' % logrotate_d,
      'olddir %s' % logrotate_backup,
    ]

    logrotate_conf_file = self.createFile(logrotate_conf_file, 
        '\n'.join(logrotate_conf))

    state_file = self.options['state-file']

    logrotate = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.execute',
      [self.options['logrotate-binary'], '-s', state_file, logrotate_conf_file, ]
    )

    return [logrotate, logrotate_conf_file]

class Part(GenericBaseRecipe):

  def install(self):

    logrotate_d = self.options['logrotate-entries']

    conf = []

    if 'post' in self.options:
      conf.append("postrotate\n%s\nendscript" % self.options['post'])
    if 'pre' in self.options:
      conf.append("prerotate\n%s\nendscript" % self.options['pre'])

    log = self.options['log']

    part_path = self.createFile(os.path.join(logrotate_d, self.options['name']),
                    "%(logfiles)s {\n%(conf)s\n}" % {
                      'logfiles': log,
                      'conf': '\n'.join(conf),
                    }
                   )

    return [part_path]
