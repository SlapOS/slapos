# -*- coding: utf-8 -*-

import errno
import os


def mkdir_p(path, mode=0o777):
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
  os.chown(path, uid, gid)
  for root, dirs, files in os.walk(path):
      for items in dirs, files:
          for item in items:
              if not os.path.islink(os.path.join(root, item)):
                  os.chown(os.path.join(root, item), uid, gid)
