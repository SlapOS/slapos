# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import errno
import os
import subprocess
import sqlite3


def mkdir_p(path, mode=0o700):
    """\
    Creates a directory and its parents, if needed.

    NB: If the directory already exists, it does not change its permission.
    """

    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def chownDirectory(path, uid, gid):
  if os.getuid() != 0:
    # we are probably inside of a webrunner
    return
  # find /opt/slapgrid -not -user 1000 -exec chown slapsoft:slapsoft {} \;
  subprocess.check_call([
      '/usr/bin/find', path, '-not', '-user', str(uid), '-exec',
      '/bin/chown', '%s:%s' % (uid, gid), '{}', ';'
  ])


def parse_certificate_key_pair(html):
  """
  Extract (certificate, key) pair from an HTML page received by SlapOS Master.
  """

  c_start = html.find("Certificate:")
  c_end = html.find("</textarea>", c_start)
  certificate = html[c_start:c_end]

  k_start = html.find("-----BEGIN PRIVATE KEY-----")
  k_end = html.find("</textarea>", k_start)
  key = html[k_start:k_end]

  return certificate, key


def string_to_boolean(string):
  """
  Return True if the value of the "string" parameter can be parsed as True.
  Return False if the value of the "string" parameter can be parsed as False.
  Otherwise, Raise.

  The parser is completely arbitrary, see code for actual implementation.
  """
  if not isinstance(string, str) and not isinstance(string, unicode):
    raise ValueError('Given value is not a string.')
  acceptable_true_values = ['true']
  acceptable_false_values = ['false']
  string = string.lower()
  if string in acceptable_true_values:
    return True
  if string in acceptable_false_values:
    return False
  else:
    raise ValueError('%s is neither True nor False.' % string)


def sqlite_connect(dburi, timeout=None):
  connect_kw = {}
  if timeout is not None:
    connect_kw['timeout'] = timeout
  conn = sqlite3.connect(dburi, **connect_kw)
  conn.text_factory = str       # allow 8-bit strings
  return conn
