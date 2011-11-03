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
import sys
import inspect
import re
import urllib
import urlparse

import pkg_resources
import zc.buildout

class GenericBaseRecipe(object):

  TRUE_VALUES = ['y', 'yes', '1', 'true']

  def __init__(self, buildout, name, options):
    """Recipe initialisation"""
    self.name = name
    self.buildout = buildout
    self.logger = logging.getLogger(name)

    self.options = options.copy() # If _options use self.optionIsTrue
    self._options(options) # Options Hook
    self.options = options.copy() # Updated options dict

    self._ws = self.getWorkingSet()

  def update(self):
    """By default update method does the same thing than install"""
    return self.install()

  def install(self):
    """Install method of the recipe. This must be overriden in child
    classes """
    raise NotImplementedError("install method is not implemented.")

  def getWorkingSet(self):
    """If you want do override the default working set"""
    egg = zc.recipe.egg.Egg(self.buildout, 'slapos.cookbook',
                                  self.options.copy())
    requirements, ws = egg.working_set()
    return ws

  def _options(self, options):
    """Options Hook method. This method can be overriden in child classes"""
    return

  def createFile(self, name, content, mode=0600):
    """Create a file with content

    The parent directory should exists, else it would raise IOError"""
    with open(name, 'w') as fileobject:
      fileobject.write(content)
      os.chmod(fileobject.name, mode)
    return os.path.abspath(name)

  def createExecutable(self, name, content, mode=0700):
    return self.createFile(name, content, mode)

  def createPythonScript(self, name, absolute_function, arguments=''):
    """Create a python script using zc.buildout.easy_install.scripts

     * function should look like 'module.function', or only 'function'
       if it is a builtin function."""
    absolute_function = tuple(absolute_function.rsplit('.', 1))
    if len(absolute_function) == 1:
      absolute_function = ('__builtin__',) + absolute_function
    if len(absolute_function) != 2:
      raise ValueError("A non valid function was given")

    module, function = absolute_function
    path, filename = os.path.split(os.path.abspath(name))

    script = zc.buildout.easy_install.scripts(
      [(filename, module, function)], self._ws, sys.executable,
      path, arguments=arguments)[0]
    return script

  def createDirectory(self, parent, name, mode=0700):
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
    # TODO: implement a real password generator which remember the last
    # call.
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
    # XXX-Antoine: I didn't find any standard module to join an url with
    # login, password, ipv6 host and port.
    # So instead of copy and past in every recipe I factorized it right here.
    netloc = ''
    if auth is not None:
      auth = tuple(auth)
      netloc = urllib.quote(str(auth[0])) # Login
      if len(auth) > 1:
        netloc += ':%s' % urllib.quote(auth[1]) # Password
      netloc += '@'

    # host is an ipv6 address whithout brackets
    if ':' in host and not re.match(r'^\[.*\]$', host):
      netloc += '[%s]' % host
    else:
      netloc += str(host)

    if port is not None:
      netloc += ':%s' % port

    url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

    return url
