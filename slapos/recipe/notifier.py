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
from hashlib import sha512
from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def install(self):
    commandline = [self.options['server-binary']]
    commandline.extend(['--callbacks', self.options['callbacks']])
    commandline.extend(['--feeds', self.options['feeds']])
    commandline.extend(['--equeue-socket', self.options['equeue-socket']])
    commandline.append(self.options['host'])
    commandline.append(self.options['port'])

    return [self.createPythonScript(self.options['wrapper'],
                                    'slapos.recipe.librecipe.execute.execute',
                                    commandline)]

class Callback(GenericBaseRecipe):

  def createCallback(self, notification_id, callback):
    callback_id = sha512(notification_id).hexdigest()
    callback = self.createFile(os.path.join(self.options['callbacks'],
                                            callback_id),
                               callback)
    return callback

  def install(self):
    return [self.createCallback(self.options['on-notification-id'],
                                self.options['callback'])]

class Notify(GenericBaseRecipe):

  def createNotifier(self, notifier_binary, executable, wrapper, **kwargs):
    if not os.path.exists(kwargs['log']):
      # Just a touch
      open(kwargs['log'], 'w').close()

    commandline = [notifier_binary,
                   '-l', kwargs['log'],
                   '--title', kwargs['title'],
                   '--feed', kwargs['feed_url'],
                   '--notification-url', kwargs['notification_url'],
                   executable]
    return self.createPythonScript(wrapper,
                                   'slapos.recipe.librecipe.execute.execute',
                                   [str(i) for i in commandline])

  def install(self):
    feedurl = self.unparseUrl(scheme='http', host=self.options['host'],
                              port=self.options['port'],
                              path='/get/%s' % self.options['name'])

    script = self.createNotifier(
      self.options['notifier-binary'],
      wrapper=self.options['wrapper'],
      executable=self.options['executable'],
      log=os.path.join(self.options['feeds'], self.options['name']),
      title=self.options['title'],
      notification_url=self.options['notify'],
      feed_url=feedurl,
    )
    return [script]
