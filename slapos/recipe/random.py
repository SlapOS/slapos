##############################################################################
#
# Copyright (c) 2016 Vifib SARL and Contributors. All Rights Reserved.
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

"""
Collects various random generators to be used in
buildout Software Releases and Instances developments.
"""

from __future__ import absolute_import

import errno
import os
import random
import string

from slapos.recipe.librecipe import GenericBaseRecipe

class Time(object):
  """Generate a random time from a 24h time clock"""

  def __init__(self, buildout, name, options):
    self.name = name
    self.buildout = buildout
    self.options = options
    self.options['time'] = "%d:%d" % (random.randint(0, 23), random.randint(0, 59))

  def install(self):
    pass

  update = install


class Mac(GenericBaseRecipe):

  def __init__(self, buildout, name, options):
    if os.path.exists(options['storage-path']):
      open_file = open(options['storage-path'], 'r')
      options['mac-address'] = open_file.read()
      open_file.close()

    if options.get('mac-address', '') == '':
      # First octet has to represent a locally administered address
      octet_list = [254] + [random.randint(0x00, 0xff) for x in range(5)]
      options['mac-address'] = ':'.join(['%02x' % x for x in octet_list])
    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def install(self):
    open_file = open(self.options['storage-path'], 'w')
    open_file.write(self.options['mac-address'])
    open_file.close()
    return [self.options['storage-path']]


def generatePassword(length):
  return ''.join(random.SystemRandom().sample(string.ascii_lowercase, length))


class Password(object):
  """Generate a password that is only composed of lowercase letters

    This recipe only makes sure that ${:passwd} does not end up in `.installed`
    file, which is world-readable by default. So be careful not to spread it
    throughout the buildout configuration by referencing it directly: see
    recipes like slapos.recipe.template:jinja2 to safely process the password.

    Options:
    - bytes: password length (default: 8 characters)
    - storage-path: plain-text persistent storage for password,
                    that can only be accessed by the user
      (default: ${buildout:parts-directory}/${:_buildout_section_name_})

    If storage-path is empty, the recipe does not save the password, which is
    fine it is saved by other means, e.g. using the publish-early recipe.
  """

  def __init__(self, buildout, name, options):
    options_get = options.get
    try:
      self.storage_path = options['storage-path']
    except KeyError:
      self.storage_path = options['storage-path'] = os.path.join(
        buildout['buildout']['parts-directory'], name)
    passwd = None
    if self.storage_path:
      try:
        with open(self.storage_path) as f:
          passwd = f.read()
      except IOError as e:
        if e.errno != errno.ENOENT:
          raise
        self.update = self.install
    if not passwd:
      passwd = self.generatePassword(int(options_get('bytes', '8')))
    self.passwd = passwd
    # Password must not go into .installed file, for 2 reasons:
    # security of course but also to prevent buildout to always reinstall.
    options.get = lambda option, *args, **kw: passwd \
      if option == 'passwd' else options_get(option, *args, **kw)

  generatePassword = staticmethod(generatePassword)

  def install(self):
    if self.storage_path:
      try:
        os.unlink(self.storage_path)
      except OSError as e:
        if e.errno != errno.ENOENT:
          raise
      fd = os.open(self.storage_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_TRUNC, 0600)
      try:
        os.write(fd, self.passwd)
      finally:
        os.close(fd)
      return self.storage_path

  def update(self):
    return ()
