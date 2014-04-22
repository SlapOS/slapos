# -*- coding: utf-8 -*-

import errno
import os
import subprocess


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
  chown_cmd = '/bin/chown'
  if os.path.exists(chown_cmd):
    subprocess.check_call([chown_cmd, '-R', '%s:%s' % (uid, gid), path])
  else:
    # slow fallback.. not unix?
    print 'chown..', path
    os.chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for items in dirs, files:
            for item in items:
                if not os.path.islink(os.path.join(root, item)):
                    os.chown(os.path.join(root, item), uid, gid)


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
