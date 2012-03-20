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
import hashlib
import shutil
import os

DEFAULT_HASH = 'sha512'

class Hash(object):

  def __init__(self, name):
    self._hash = hashlib.new(name)

  def write(self, data):
    self._hash.update(data)

  def read(self):
    return self._hash.hexdigest()

def filehash(filename, type_=DEFAULT_HASH):
  if not os.path.isfile(filename):
    raise ValueError("%r isn't a file" % filename)

  digest = Hash(type_)
  with open(filename, 'r') as file_:
    shutil.copyfileobj(file_, digest)
  return digest.read()

# Home made hashdeep <http://md5deep.sourceforge.net/>
def dirhash(dirname, type_=DEFAULT_HASH):
  """Walk into a directory an return a unique hash for
  the directory structure and its files content."""

  if not os.path.isdir(dirname):
    raise ValueError("%r isn't a directory" % dirname)

  digest = Hash(type_)

  # List the directory structure
  path_list = []
  for dirname, dirlist, filelist in os.walk(dirname, followlinks=False):
    for filename in filelist:
      path_list.append(os.path.join(dirname, filename))
  path_list.sort()

  for path in path_list:
    # Change the hash even if the file or the directory is empty
    digest.write(path)

    # Update the hash with file content
    if os.path.isfile(path):
      with open(path, 'r') as file_:
        shutil.copyfileobj(file_, digest)

  return digest.read()

def pathhash(path, type_=DEFAULT_HASH):
  if os.path.isdir(path):
    return dirhash(path, type_)
  elif os.path.isfile(path):
    return filehash(path, type_)
  raise ValueError("%r isn't a directory nor a file" % path)

# you can use python -m slapos.recipe.librecipe.filehash [hash] path
if __name__ == '__main__':
  import sys
  if len(sys.argv) == 1:
    raise ValueError("Not enough command line arguments")
  if len(sys.argv) == 2:
    print sys.argv[1], '-', pathhash(sys.argv[1])
  else:
    print sys.argv[2], '-', pathhash(sys.argv[2], sys.argv[1])
