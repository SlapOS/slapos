##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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
import pprint
import re
import subprocess

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  """\
  Configure a Mioga instance:

  - call "make install-all"
  """

  def install(self):
    print "This is the Mioga recipe"
    print "Looking for compile folder:"
    print self.options['mioga_compile_dir']

    # TODO: this will only work for a SINGLE instance in the Slaprunner.
    # In a real environment we cannot mess around with the compile directory
    # like that.    
    former_directory = os.getcwd()
    os.chdir(self.options['mioga_compile_dir'])

    vardir = self.options['var_directory']
    mioga_base = os.path.join(vardir, 'lib', 'Mioga2')
    fm = FileModifier('conf/Config.xml')
    fm.modify('install_dir', mioga_base)
    fm.modify('tmp_dir', os.path.join(mioga_base, 'tmp'))
    fm.modify('search_tmp_dir', os.path.join(mioga_base, 'mioga_search'))
    fm.modify('maildir', os.path.join(vardir, 'spool', 'mioga', 'maildir'))
    fm.modify('maildirerror', os.path.join(vardir, 'spool', 'mioga', 'error'))
    fm.modify('mailfifo', os.path.join(vardir, 'spool', 'mioga', 'fifo'))
    fm.modify('dbi_passwd', self.options['db_password'])
    fm.modify('db_host', self.options['db_host'])
    fm.modify('db_port', self.options['db_port'])
    # TODO: Mioga must be able to use an external Postgres server! IPv6 address!
    fm.save()
    os.remove("config.mk") # otherwise we don't see the values in the Makefiles

    environ = os.environ
    environ['PATH'] = self.options['mioga_add_to_path'] + ':' + environ['PATH']
    # environ = self.options['mioga_compile_env']
    print pprint.pformat(environ)

    # We must call "make installall" in the SAME environment that
    # "perl Makefile.PL" left!

    cmd = subprocess.Popen(self.options['perl_binary'] + ' Makefile.PL'
                           + ' && make installall',
                           env=environ, shell=True)
    cmd.communicate()
    
    # cmd_configure = subprocess.Popen([ self.options['perl_binary'],
    #                                    'Makefile.PL' ],
    #                                  env=environ)
    # cmd_configure.communicate()

    # if cmd_configure.returncode == 0:
    #   # TODO: no "make" on SlapOS ?
    #   cmd_make = subprocess.Popen(['make', 'installall'],
    #                               env=environ)
    #   cmd_make.communicate()
    # else:
    #   print "Mioga instantiate.py::install: Configure failed."

    os.chdir(former_directory)
    print "Mioga instantiate.py::install finished!"


# Copied verbatim from mioga-hooks.py - how to reuse code?
class FileModifier:
  def __init__(self, filename):
    self.filename = filename
    f = open(filename, 'rb')
    self.content = f.read()
    f.close()
  
  def modify(self, key, value):
    (self.content, count) = re.subn(
      r'(<parameter[^>]*\sname\s*=\s*"' + re.escape(key) + r'"[^>]*\sdefault\s*=\s*")[^"]*',
      r"\g<1>" + value,
      self.content)
    return count
      
  def save(self):
    f = open(self.filename, 'w')
    f.write(self.content)
    f.close()
