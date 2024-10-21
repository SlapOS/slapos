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
import json
import os
import random
import string
import sys
from .librecipe import GenericBaseRecipe
from .publish_early import volatileOptions

import passlib.hash


class Integer(object):
  """
  Generate a random integer (see standard random.randint documentation).

  Input options:
  minimum (required)
    integer(-ish) minmum bound, included.
  maximum (required)
    integer(-ish) maximum bound, included.

  Output options:
  value
    Resulting integer.
  """
  def __init__(self, buildout, name, options):
    if 'value' not in options:
      options['value'] = random.randint(int(options['minimum']),
                                        int(options['maximum']))

  def install(self):
    pass

  update = install

class Time(object):
  """Generate a random time from a 24h time clock"""

  def __init__(self, buildout, name, options):
    if 'time' not in options:
      options['time'] = "%u:%02u" % (
        random.randint(0, 23), random.randint(0, 59))

  def install(self):
    pass

  update = install


class Mac(object):

  def __init__(self, buildout, name, options):
    self.storage_path = options['storage-path']
    mac = options.get('mac-address')
    if not mac:
      try:
        with open(self.storage_path) as f:
          mac = f.read()
      except IOError as e:
        if e.errno != errno.ENOENT:
          raise
      if not mac:
        # First octet has to represent a locally administered address
        octet_list = [254] + [random.randint(0x00, 0xff) for x in range(5)]
        mac = ':'.join(['%02x' % x for x in octet_list])
        self.update = self.install
      options['mac-address'] = mac
    self.mac = mac

  def install(self):
    with open(self.storage_path, 'w') as f:
      f.write(self.mac)
    return self.storage_path

  def update(self):
    pass

def generatePassword(length):
  system_random = random.SystemRandom()
  alphabet = string.ascii_letters + string.digits
  return ''.join(system_random.choice(alphabet) for i in range(length))


class Password(object):
  """Generate a password.

    This recipe only makes sure that ${:passwd} does not end up in `.installed`
    file, which is world-readable by default. So be careful not to spread it
    throughout the buildout configuration by referencing it directly: see
    recipes like slapos.recipe.template:jinja2 to safely process the password.

    Options:
    - bytes: password length (default: 16 characters)
    - storage-path: plain-text persistent storage for password,
                    that can only be accessed by the user
      (default: ${buildout:parts-directory}/${:_buildout_section_name_})
    - create-once: boolean value which set if storage-path won't be modified
                   as soon the file is created with the password (not empty).
      (default: True)
    - passwd: the generated password. Can also be set, to reuse the password
              hashing capabilities.
    - passwd-*: the hashed password, using schemes supported by passlib.
                for example, passwd-sha256-crypt will expose the password hashed
                with sha256 crypt algorithm.

    If storage-path is empty, the recipe does not save the password, which is
    fine it is saved by other means, e.g. using the publish-early recipe.
  """

  def __init__(self, buildout, name, options):
    self.create_once = options.get('create-once', 'True').lower() \
          in GenericBaseRecipe.TRUE_VALUES
    try:
      self.storage_path = options['storage-path']
    except KeyError:
      self.storage_path = options['storage-path'] = os.path.join(
        buildout['buildout']['parts-directory'], name)

    passwd_option = options.get('passwd')
    passwd_dict = {'': passwd_option}
    if self.storage_path:
      try:
        with open(self.storage_path) as f:
          content = f.read().strip('\n')
          # new format: the file contains password and hashes in json format
          try:
            passwd_dict = json.loads(content)
            if sys.version_info < (3, ):
              passwd_dict = {k: v.encode('utf-8') for k, v in passwd_dict.items()}
          except ValueError:
            # old format: the file only contains the password in plain text
            passwd_dict[''] = content
      except IOError as e:
        if e.errno != errno.ENOENT:
          raise
      if passwd_option and passwd_dict[''] != passwd_option:
        passwd_dict = {'': passwd_option}

    if not passwd_dict['']:
      passwd_dict[''] = self.generatePassword(int(options.get('bytes', '16')))
      self.update = self.install
    options['passwd'] = passwd_dict['']

    class HashedPasswordDict(dict):
      def __missing__(self, key):
        if not key.startswith('passwd-'):
          raise KeyError(key)
        if key in passwd_dict:
          return passwd_dict[key]
        handler = getattr(
          passlib.hash, key[len('passwd-'):].replace('-', '_'), None)
        if handler is None:
          raise KeyError(key)
        hashed = handler.hash(passwd_dict[''])
        passwd_dict[key] = hashed
        return hashed
    options._data = HashedPasswordDict(options._data)

    # Password must not go into .installed file, for 2 reasons:
    # security of course but also to prevent buildout to always reinstall.
    # publish_early already does it, but this recipe may also be used alone.
    volatileOptions(options, ('passwd',))
    self.passwd_dict = passwd_dict

  generatePassword = staticmethod(generatePassword)

  def install(self):
    if self.storage_path:
      serialized = json.dumps(self.passwd_dict, sort_keys=True)
      stored = None
      try:
        with open(self.storage_path) as f:
          stored = f.read()
      except IOError as e:
        if e.errno != errno.ENOENT:
          raise
      if stored != serialized:
        with open(self.storage_path, 'w') as f:
          f.write(serialized)
      if not self.create_once:
        return self.storage_path

  def update(self):
    pass
