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
import shutil
import signal
import stat
import subprocess

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  """\
  Configure a Mioga instance:

  - call "make install-all"
  """

  def removeIfExisting(self, filepath):
    if os.path.isfile(filepath):
      os.remove(filepath)

  def install(self):
    self.instantiate(True)

  def update(self):
    self.instantiate(False)

  def instantiate(self, isNewInstall):
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
    fm.modify('notifierfifo', os.path.join(vardir, 'spool', 'mioga', 'notifier'))
    fm.modify('searchenginefifo', os.path.join(vardir, 'spool', 'mioga', 'searchengine'))
    fm.modify('dbi_passwd', self.options['db_password'])
    fm.modify('db_host', self.options['db_host'])
    fm.modify('db_port', self.options['db_port'])
    fm.modify('dav_host', self.options['private_ipv4'])
    fm.modify('dav_port', self.options['public_ipv6_port'])
    # db_name, dbi_login are standard
    fm.save()
    # Ensure no old data is kept
    self.removeIfExisting('config.mk')
    if os.path.isdir('web/conf/apache'):
      shutil.rmtree('web/conf/apache')

    environ = os.environ
    environ['PATH'] = ':'.join([self.options['perl_bin'],           # priority!
                                self.options['mioga_add_to_path'],
                                self.options['postgres_bin'],
                                environ['PATH'] ])
    
    # Write the Postgres password file
    pgpassfilepath = os.path.join(self.options['instance_root'], '.pgpass')
    pgpassfile = open(pgpassfilepath, 'w')
    pgpassfile.write(':'.join([re.sub(r':', r'\:', self.options['db_host']),
                               self.options['db_port'],
                               '*', # could be self.options['db_dbname'] or 'postgres'
                               self.options['db_username'],
                               self.options['db_password'] ]) + "\n")
    pgpassfile.close()
    os.chmod(pgpassfilepath, stat.S_IRUSR | stat.S_IWUSR)
    environ['PGPASSFILE'] = pgpassfilepath
    
    # environ = self.options['mioga_compile_env']
    print pprint.pformat(environ)

    # We must call "make installall" in the SAME environment that
    # "perl Makefile.PL" left!

    cmd = subprocess.Popen(self.options['perl_bin'] + '/perl Makefile.PL'
                           + ' && make installall',
                           env=environ, shell=True)
    cmd.communicate()

    # Apache configuration!
    # Take the files that Mioga has prepared, and wrap some standard configuration around it.
    # TODO: can't we squeeze this somehow into the generic apacheperl recipe?
    apache_config_mioga = '''
LoadModule alias_module modules/mod_alias.so
LoadModule apreq_module modules/mod_apreq2.so
LoadModule auth_basic_module modules/mod_auth_basic.so
LoadModule authz_default_module modules/mod_authz_default.so
LoadModule authz_host_module modules/mod_authz_host.so
LoadModule authz_user_module modules/mod_authz_user.so
LoadModule dav_module modules/mod_dav.so
LoadModule dav_fs_module modules/mod_dav_fs.so
LoadModule dav_lock_module modules/mod_dav_lock.so
LoadModule deflate_module modules/mod_deflate.so
LoadModule dir_module modules/mod_dir.so
LoadModule env_module modules/mod_env.so
LoadModule headers_module modules/mod_headers.so
LoadModule log_config_module modules/mod_log_config.so
LoadModule perl_module modules/mod_perl.so

# Basic server configuration
# TODO: how to listen to standard port 80 when we are not root?
PidFile REPL_PID
Listen [REPL_IPV6HOST]:REPL_IPV6PORT
Listen REPL_IPV4HOST:REPL_IPV6PORT
# Listen [REPL_IPV6]:443 # what about mod_ssl and all that stuff?
# ServerAdmin someone@email

# Log configuration
ErrorLog REPL_ERRORLOG
LogLevel debug
LogFormat "%h %{REMOTE_USER}i %l %u %t \\"%r\\" %>s %b \\"%{Referer}i\\" \\"%{User-Agent}i\\"" combined
LogFormat "%h %{REMOTE_USER}i %l %u %t \\"%r\\" %>s %b" common
CustomLog REPL_ACCESSLOG common
DocumentRoot REPL_DOCROOT
DirectoryIndex index.html
DavLockDB REPL_DAVLOCK
'''
    apache_config_mioga = (apache_config_mioga
     .replace('REPL_PID', self.options['pid_file'])
     .replace('REPL_IPV6HOST', self.options['public_ipv6'])
     .replace('REPL_IPV4HOST', self.options['private_ipv4'])
     .replace('REPL_IPV6PORT', self.options['public_ipv6_port'])
     .replace('REPL_ERRORLOG', self.options['error_log'])
     .replace('REPL_ACCESSLOG', self.options['access_log'])
     .replace('REPL_DOCROOT', self.options['htdocs'])
     .replace('REPL_STATIC', os.path.join(mioga_base, 'static')) 
     .replace('REPL_DAVLOCK', self.options['dav_locks']) )

    mioga_prepared_apache_config_dir = os.path.join(mioga_base, 'conf', 'apache')
    for filepath in os.listdir(mioga_prepared_apache_config_dir):
      apache_config_mioga += ("# Read in from "+filepath+"\n" + 
        open(os.path.join(mioga_prepared_apache_config_dir, filepath)).read() + "\n" )
    # Internal DAV only accepts its own IPv6 address
    # TODO: check with what sender address we really arrive at the DAV locations.
    apache_config_mioga = re.sub(
      'Allow from localhost', 
      "Allow from "+self.options['private_ipv4']+"\n\tAllow from "+self.options['public_ipv6'],
      apache_config_mioga)
    
    path_list = []
    open(self.options['httpd_conf'], 'w').write(apache_config_mioga)
    # TODO: if that all works fine, put it into a proper template
    # httpd_conf = self.createFile(self.options['httpd_conf'],
    #   self.substituteTemplate(self.getTemplateFilename('apache.in'),
    #                           apache_config)
    # )
    path_list.append(os.path.abspath(self.options['httpd_conf']))

    wrapper = self.createPythonScript(self.options['wrapper'],
        'slapos.recipe.librecipe.execute.execute',
        [self.options['httpd_binary'], '-f', self.options['httpd_conf'],
         '-DFOREGROUND']
    )
    path_list.append(wrapper)

    if os.path.exists(self.options['pid_file']):
      # Reload apache configuration
      with open(self.options['pid_file']) as pid_file:
        pid = int(pid_file.read().strip(), 10)
      try:
        os.kill(pid, signal.SIGUSR1) # Graceful restart
      except OSError:
        pass

    os.chdir(former_directory)
    print "Mioga instantiate.py::install finished!"
    return path_list



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
