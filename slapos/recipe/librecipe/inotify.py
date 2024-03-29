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
import logging
import os
import time

from inotify_simple import INotify, flags

logger = logging.getLogger(__name__)

def subfiles(directory):
  """Return the list of subfiles of a directory, and wait for the newly created
  ones.

  CAUTION : *DONT TRY TO CONVERT THE RESULT OF THIS FUNCTION INTO A LIST !
  ALWAYS ITERATE OVER IT !!!*"""

  with INotify() as inotify:
    try:
      inotify.add_watch(directory, flags.CLOSE_WRITE | flags.MOVED_TO)
      inotify_available = True
    except OSError:
      logger.warning("Unable to add inotify watch, falling back to polling")
      inotify_available = False

    names = os.listdir(directory)
    while True:
      for name in names:
        yield os.path.join(directory, name)
      if inotify_available:
        names = (event.name for event in inotify.read())
      else:
        time.sleep(5)
        names = os.listdir(directory)
