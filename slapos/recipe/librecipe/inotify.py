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

import inotifyx

def subfiles(directory):
  """Return the list of subfiles of a directory, and wait for the newly created
  ones.

  CAUTION : *DONT TRY TO CONVERT THE RESULT OF THIS FUNCTION INTO A LIST !
  ALWAYS ITERATE OVER IT !!!*"""
  watchfd = inotifyx.init()
  inotifyx.add_watch(watchfd, directory, inotifyx.IN_CREATE)
  try:

    subfiles = set(os.listdir(directory))
    subfiles |= set([file_.name for file_ in inotifyx.get_events(watchfd, 0)])

    while True:
      for file_ in subfiles:
        yield os.path.join(directory, file_)

      subfiles = [file_.name for file_ in inotifyx.get_events(watchfd)]

  finally:
    os.close(watchfd)
