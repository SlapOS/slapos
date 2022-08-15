# -*- coding: utf-8 -*-
# vim: set et sts=2:
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
import errno
import logging
import os
import sys
import inspect
import re
import stat
from six.moves.urllib.parse import quote
import itertools
import six
from six.moves import map
from six.moves.urllib.parse import urlunparse


import pkg_resources
from zc.buildout import easy_install, UserError
from zc.recipe.egg import Egg

from slapos.recipe.librecipe import shlex

class GenericBaseRecipe(object):
  """Boilerplate class for all Buildout recipes providing helpful methods like
     creating configuration file, creating wrappers, generating passwords, etc.
     Can be extended in SlapOS recipes to ease development.
  """

  TRUE_VALUES = ['y', 'yes', '1', 'true']
  FALSE_VALUES = ['n', 'no', '0', 'false']

  def __init__(self, buildout, name, options):
    """Recipe initialisation"""
    self.name = name
    self.buildout = buildout
    self.logger = logging.getLogger(name)

    self.options = options.copy() # If _options use self.optionIsTrue
    self._options(options) # Options Hook
    self.options = options.copy() # Updated options dict

  @property
  def _ws(self):
    # getWorkingSet() is slow and it is not always needed.
    # So _ws should be a lazy attribute.
    if getattr(self, '_ws_internal', None) is None:
      self._ws_internal = self.getWorkingSet()
    return self._ws_internal

  def update(self):
    """By default update method does the same thing than install"""
    return self.install()

  def install(self):
    """Install method of the recipe. This must be overriden in child
    classes """
    raise NotImplementedError("install method is not implemented.")

  def getWorkingSet(self):
    """If you want do override the default working set"""
    egg = Egg(self.buildout, 'slapos.cookbook', self.options.copy())
    requirements, ws = egg.working_set()
    return ws

  def _options(self, options):
    """Options Hook method. This method can be overriden in child classes"""
    return

  def createFile(self, name, content, mode=0o600):
    """Create a file with content

    The parent directory should exists, else it would raise IOError"""
    if not isinstance(content, bytes):
      content = content.encode('utf-8')
    # Try to reuse existing file. This is particularly
    # important to avoid excessive IO during update.
    try:
      with open(name, 'rb') as f:
        if f.read(len(content)+1) == content:
          if None is not mode != stat.S_IMODE(os.fstat(f.fileno()).st_mode):
            os.fchmod(f.fileno(), mode)
          return os.path.abspath(name)
    except (IOError, OSError) as e:
      pass
    try:
      os.unlink(name)
    except OSError as e:
      if e.errno != errno.ENOENT:
        raise
    with open(name, 'wb') as f:
      if mode is not None:
        os.fchmod(f.fileno(), mode)
      f.write(content)
    return os.path.abspath(name)

  def createExecutable(self, name, content, mode=0o700):
    return self.createFile(name, content, mode)

  def createPythonScript(self, name, absolute_function, args=(), kw={}):
    """Create a python script using zc.buildout.easy_install.scripts

     * function should look like 'module.function', or only 'function'
       if it is a builtin function."""
    function = absolute_function.rsplit('.', 1)
    if len(function) == 1:
      module = '__builtin__'
      function, = function
    else:
      module, function = function
    path, filename = os.path.split(os.path.abspath(name))

    assert not isinstance(args, (six.string_types, dict)), args
    args = itertools.chain(map(repr, args),
                           map('%s=%r'.__mod__, six.iteritems(kw)))

    return easy_install.scripts(
      [(filename, module, function)], self._ws, sys.executable,
      path, arguments=', '.join(args))[0]

  def parsePrivateTmpfs(self):
    private_tmpfs = []
    for line in (self.options.get('private-tmpfs') or '').splitlines():
      if line:
        x = line.split(None, 1)
        if len(x) != 2:
          raise UserError("failed to split %r into size and path" % line)
        private_tmpfs.append(tuple(x))
    return private_tmpfs

  def createWrapper(self, path, args, env=None, **kw):
    """Create a wrapper script for process replacement"""
    assert args
    if kw:
      return self.createPythonScript(path,
        'slapos.recipe.librecipe.execute.generic_exec',
        (args, env) if env else (args,), kw)

    # Simple case: creates a basic shell script for process replacement.
    # This must be kept minimal to avoid code duplication with generic_exec.
    # In particular, do not implement workaround for shebang size limitation
    # here (note that this can't be done correctly with a POSIX shell, because
    # the process can't be given a name).

    lines = ['#!/bin/sh']

    if env:
      for k, v in sorted(six.iteritems(env)):
        lines.append('export %s=%s' % (k, shlex.quote(v)))

    lines.append('exec')

    args = list(map(shlex.quote, args))
    args.append('"$@"')
    for arg in args:
      if len(lines[-1]) < 40:
        lines[-1] += ' ' + arg
      else:
        lines[-1] += ' \\'
        lines.append('\t' + arg)

    lines.append('')
    return self.createFile(path, '\n'.join(lines), 0o700)

  def createDirectory(self, parent, name, mode=0o700):
    path = os.path.join(parent, name)
    if not os.path.exists(path):
      os.mkdir(path, mode)
    elif not os.path.isdir(path):
      raise OSError("%r exists but is not a directory." % name)
    return path

  def substituteTemplate(self, template_location, mapping_dict):
    """Read from file template_location an substitute content with
       mapping_dict doing a dummy python format."""
    with open(template_location, 'r') as template:
      return template.read() % mapping_dict

  def getTemplateFilename(self, template_name):
    caller = inspect.stack()[1]
    caller_frame = caller[0]
    name = caller_frame.f_globals['__name__']
    return pkg_resources.resource_filename(name,
        'template/%s' % template_name)

  def generatePassword(self, len_=32):
    # TODO: Consider having generate.password recipe inherit this class,
    #       so that it can be easily inheritable.
    #       In the long-term, it's probably better that passwords are provided
    #       by software requesters, to avoid keeping unhashed secrets in
    #       partitions when possible.
    self.logger.warning("GenericBaseRecipe.generatePassword is deprecated."
                        " Use generate.password recipe instead.")
    return "insecure"

  def isTrueValue(self, value):
    return str(value).lower() in GenericBaseRecipe.TRUE_VALUES

  def optionIsTrue(self, optionname, default=None):
    if default is not None and optionname not in self.options:
      return default
    return self.isTrueValue(self.options[optionname])

  def unparseUrl(self, scheme, host, path='', params='', query='',
                 fragment='', port=None, auth=None):
    """Join a url with auth, host, and port.

    * auth can be either a login string or a tuple (login, password).
    * if the host is an ipv6 address, brackets will be added to surround it.

    """
    netloc = ''
    if auth is not None:
      auth = tuple(auth)
      netloc = quote(str(auth[0])) # Login
      if len(auth) > 1:
        netloc += ':%s' % quote(auth[1]) # Password
      netloc += '@'

    # host is an ipv6 address whithout brackets
    if ':' in host and not re.match(r'^\[.*\]$', host):
      netloc += '[%s]' % host
    else:
      netloc += str(host)

    if port is not None:
      netloc += ':%s' % port

    url = urlunparse((scheme, netloc, path, params, query, fragment))

    return url
