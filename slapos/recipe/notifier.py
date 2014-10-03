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
    options = self.options
    script = self.createWrapper(name=options['wrapper'],
                                command=options['server-binary'],
                                parameters=[
                                   '--callbacks', options['callbacks'],
                                   '--feeds', options['feeds'],
                                   '--equeue-socket', options['equeue-socket'],
                                   options['host'], options['port']
                                   ],
                                comments=[
                                    '',
                                    'Upon receiving a notification, execute the callback(s).',
                                    ''])
    return [script]


class Callback(GenericBaseRecipe):

  def createCallback(self, notification_id, callback):
    # XXX: hashing the name here and in
    # slapos.toolbox/slapos/pubsub/__init__.py is completely messed up and
    # prevent any debug.
    callback_id = sha512(notification_id).hexdigest()

    filepath = os.path.join(self.options['callbacks'], callback_id)
    self.addLineToFile(filepath, callback)
    return filepath

  def install(self):
    # XXX this path is returned multiple times, one for each callback that has been added.
    return [self.createCallback(self.options['on-notification-id'],
                                self.options['callback'])]

class Notify(GenericBaseRecipe):

  def createNotifier(self, notifier_binary, wrapper, executable,
                     log, title, notification_url, feed_url, pidfile=None):

    if not os.path.exists(log):
      # Just a touch
      open(log, 'w').close()

    parameters = [
            '-l', log,
            '--title', title,
            '--feed', feed_url,
            '--notification-url',
            ]
    parameters.extend(notification_url.split(' '))
    parameters.extend(['--executable', executable])

    return self.createWrapper(name=wrapper,
                              command=notifier_binary,
                              parameters=parameters,
                              pidfile=pidfile,
                              parameters_extra=True,
                              comments=[
                                  '',
                                  'Call an executable and send notification(s).',
                                  ''])


  def install(self):
    feed_url = self.unparseUrl(scheme='http', host=self.options['host'],
                               port=self.options['port'],
                               path='/get/%s' % self.options['name'])

    log = os.path.join(self.options['feeds'], self.options['name'])

    options = self.options
    script = self.createNotifier(notifier_binary=options['notifier-binary'],
                                 wrapper=options['wrapper'],
                                 executable=options['executable'],
                                 log=log,
                                 title=options['title'],
                                 pidfile=options['pidfile'],
                                 notification_url=options['notify'],
                                 feed_url=feed_url)
    return [script]
