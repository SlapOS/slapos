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
#############################################################################

import os
import sys
import zc.buildout
from slapos.recipe.librecipe import BaseSlapRecipe

class Recipe(BaseSlapRecipe):
  def _install(self):
    """Set the connection dictionnary for the computer partition and create a list
    of paths to the different wrappers."""
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()

    self.installTestrunner(self.getDisplay())
    self.linkBinary()

    return self.path_list

  def getDisplay(self):
    """Generate display id for the instance."""
    display_list = [":%s" % i for i in range(123,144)]
    for display_try in display_list:
      lock_filepath = '/tmp/.X%s-lock' % display_try.replace(":", "")
      if not os.path.exists(lock_filepath):
        display = display_try
        break
    return display

  def installTestrunner(self, display):
    """Instanciate a wrapper for the browser and the test reports."""
    arguments = dict(
        xvfb_binary    = self.options['xvfb_binary'],
        display        = display,
        suite_name     = self.parameter_dict['suite_name'],
        base_url       = self.parameter_dict['url'],
        browser_argument_list = [],
        user           = self.parameter_dict['user'],
        password       = self.parameter_dict['password'],
        project       = self.parameter_dict['project'],
        test_report_instance_url = \
            self.parameter_dict['test_report_instance_url'],
        etc_directory  = self.etc_directory)

    # Check wanted browser XXX-Cedric not yet used but can be useful
    #if self.parameter_dict.get('browser', None) is None:
    arguments['browser_binary'] = self.options['firefox_binary']
    #elif self.parameter_dict['browser'].strip().lowercase() == 'chrome' or
    #    self.parameter_dict['browser'].strip().lowercase() == 'chromium':
    #  arguments['browser_binary'] = self.options['chromium_binary']
    #  arguments['browser_argument_list'].extend['--ignore-certificate-errors',
    #      option_translate = '--disable-translate',
    #      option_security = '--disable-web-security']
    #elif self.parameter_dict['browser'].strip().lowercase() == 'firefox':
    #  arguments['browser_binary'] = self.options['firefox_binary']

    self.path_list.extend(zc.buildout.easy_install.scripts([(
        'testrunner',__name__+'.testrunner', 'run')], self.ws,
        sys.executable, self.wrapper_directory,
        arguments=[arguments]))

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
            'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)
