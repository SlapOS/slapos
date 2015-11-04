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
    path_list = []

    if not self.optionIsTrue('use_passwd', False):
      master_passwd = "# masterauth <master-password>"
    else:
      master_passwd = "masterauth %s" % self.options['passwd']
    config_file = self.options['config_file'].strip()
    configuration = dict(pid_file=self.options['pid_file'],
                        port=self.options['port'],
                        ipv6=self.options['ipv6'],
                        server_dir=self.options['server_dir'],
                        log_file=self.options['log_file'],
                        master_passwd=master_passwd
    )
    if self.options.get('unixsocket'):
        unixsocket = "unixsocket %s\nunixsocketperm 700" % self.options['unixsocket']
    else:
        unixsocket = ""
    configuration['unixsocket'] = unixsocket

    config = self.createFile(config_file,
      self.substituteTemplate(self.getTemplateFilename('redis.conf.in'),
      configuration))
    path_list.append(config)

    redis = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.execute',
      [self.options['server_bin'], config_file]
    )
    path_list.append(redis)

    promise_script = self.options.get('promise_wrapper', '').strip()
    if promise_script:
      promise = self.createPythonScript(
        promise_script,
        '%s.promise.main' % __name__,
        dict(host=self.options['ipv6'], port=self.options['port'],
             unixsocket = self.options.get('unixsocket') )
      )
      path_list.append(promise)

    return path_list

