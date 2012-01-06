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
import sys
import subprocess

import inotifyx

from slapos.recipe.librecipe import GenericBaseRecipe

class LockFile(object):

  class LockException(Exception):
    pass

  def __init__(self, filename, wait=True, exit=False):
    self.filename = filename
    if wait:
      self.callback = lambda: self.waitDeletion()
    elif not exit:
      self.callback = lambda: self.raiseException()
    else:
      self.callback = lambda: sys.exit(1)

  def raiseException(self):
    raise LockFile.LockException("Not able to lock the file")

  def waitDeletion(self):
    inotify_fd = inotifyx.init()
    try:
      inotifyx.add_watch(inotify_fd, self.filename, inotifyx.IN_DELETE)
      inotifyx.get_events(inotify_fd)
    except IOError: # add_watch failed
      pass
    finally:
      os.close(inotify_fd)

    self.__enter__()

  def __enter__(self):
    try:
      # Atomic file acquisition
      self._fd = os.open(self.filename, os.O_CREAT | os.O_EXCL)
    except OSError:
      self.callback()

  def __exit__(self, exc_type, exc_value, traceback):
    os.close(self._fd)
    os.unlink(self.filename)

def locked_run(args):
  with LockFile(args['filename'], wait=args['wait'], exit=True):
    subprocess.check_call([args['binary']])

class Recipe(GenericBaseRecipe):

  def install(self):
    wrapper = self.createPythonScript(self.options['wrapper'],
                                      __name__ + '.locked_run',
                                      dict(
                                        filename=self.options['lock-file'],
                                        wait=self.optionIsTrue('wait', False),
                                        binary=self.options['binary'],
                                      )
                                     )
    return [wrapper]
