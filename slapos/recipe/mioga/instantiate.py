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

  - copy over /var and /buildinst directories
  - call "make install-all"
  """

  def removeIfExisting(self, filepath):
    if os.path.isfile(filepath):
      os.remove(filepath)

  def rsync_dir(self, src, target):
    if os.path.isdir(src) and not src.endswith('/'):
      src += '/'
    cmd = subprocess.Popen(self.options['rsync_bin'] + '/rsync -a --specials '
                           + src + ' ' + target, 
                           env=os.environ, shell=True)
    cmd.communicate()
    

  # Even if there is a dedicated update(), this is still called sometimes.
  # So better not trust that and decide for ourselves.
  def install(self):
    self.options['admin_password'] = 'test_for_programmatic_setting'
    # Copy the build/ and var/lib/Mioga2 folders into the instance
    mioga_location = self.options['mioga_location']

    var_dir = self.options['var_directory']
    self.rsync_dir(os.path.join(mioga_location, 'var'), var_dir)
    
    buildinst_dir = self.options['buildinst_directory']
    self.rsync_dir(self.options['mioga_buildinst'], buildinst_dir)
    
    former_directory = os.getcwd()
    os.chdir(buildinst_dir)

    vardir = self.options['var_directory']
    mioga_base = os.path.join(vardir, 'lib', 'Mioga2')
    fm = FileModifier('conf/Config.xml')
    fm.modifyParameter('init_sql', 'no') # force_init_sql is set manually everywhere
    fm.modifyParameter('install_dir', mioga_base)
    fm.modifyParameter('tmp_dir', os.path.join(mioga_base, 'tmp'))
    fm.modifyParameter('search_tmp_dir', os.path.join(mioga_base, 'mioga_search'))
    fm.modifyParameter('maildir', os.path.join(vardir, 'spool', 'mioga', 'maildir'))
    fm.modifyParameter('maildirerror', os.path.join(vardir, 'spool', 'mioga', 'error'))
    fm.modifyParameter('mailfifo', os.path.join(vardir, 'spool', 'mioga', 'fifo'))
    notifier_fifo = os.path.join(vardir, 'spool', 'mioga', 'notifier')
    fm.modifyParameter('notifierfifo', notifier_fifo)
    searchengine_fifo = os.path.join(vardir, 'spool', 'mioga', 'searchengine')
    fm.modifyParameter('searchenginefifo', searchengine_fifo)
    fm.modifyParameter('dbi_passwd', self.options['db_password'])
    fm.modifyParameter('db_host', self.options['db_host'])
    fm.modifyParameter('db_port', self.options['db_port'])
    fm.modifyParameter('dav_host', self.options['public_ipv6'])
    fm.modifyParameter('dav_port', self.options['public_ipv6_port'])
    fm.modifyParameter('bin_dir', self.options['bin_dir'])
    # db_name, dbi_login are standard
    fm.save()
    # Ensure no old data is kept
    self.removeIfExisting('config.mk')
    # if os.path.isdir('web/conf/apache'):
    #   shutil.rmtree('web/conf/apache')

    environ = os.environ
    environ['PATH'] = ':'.join([self.options['perl_bin'],           # priority!
                                # Mioga scripts in Makefiles and shell scripts
                                self.options['bin_dir'],            
                                self.options['libxslt_bin'],
                                self.options['libxml2_bin'],
                                self.options['postgres_bin'],
                                self.options['rsync_bin'],
                                environ['PATH'] ])
    environ['MIOGA_SITEPERL'] = self.options['mioga_siteperl']
    
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
    
    # We must call "make" in the SAME environment that
    # "perl Makefile.PL" left!

    cmd = subprocess.Popen(self.options['perl_bin'] + '/perl Makefile.PL disable_check'
                           + ' && make slapos-instantiation',
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
LoadModule autoindex_module modules/mod_autoindex.so
LoadModule dav_module modules/mod_dav.so
LoadModule dav_fs_module modules/mod_dav_fs.so
LoadModule dav_lock_module modules/mod_dav_lock.so
LoadModule deflate_module modules/mod_deflate.so
LoadModule dir_module modules/mod_dir.so
LoadModule env_module modules/mod_env.so
LoadModule headers_module modules/mod_headers.so
LoadModule log_config_module modules/mod_log_config.so
LoadModule mime_module modules/mod_mime.so
LoadModule perl_module modules/mod_perl.so

# Basic server configuration
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

Include conf/extra/httpd-autoindex.conf
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
    # Internal DAV only accepts its own addresses
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

    services_dir = self.options['services_dir']

    httpd_wrapper = self.createPythonScript(
      os.path.join(services_dir, 'httpd_wrapper'),
      'slapos.recipe.librecipe.execute.execute',
      [self.options['httpd_binary'], '-f', self.options['httpd_conf'],
       '-DFOREGROUND']
    )
    path_list.append(httpd_wrapper)

    for fifo in [notifier_fifo, searchengine_fifo]:
      if os.path.exists(fifo):
        if not stat.S_ISFIFO(os.stat(fifo).st_mode):
          raise Exception("The file "+fifo+" exists but is not a FIFO.")
      else:
        os.mkfifo(fifo, 0600)

    site_perl_bin = os.path.join(self.options['site_perl'], 'bin')
    mioga_conf_path = os.path.join(mioga_base, 'conf', 'Mioga.conf')
    notifier_wrapper = self.createPythonScript(
      os.path.join(services_dir, 'notifier'),
      'slapos.recipe.librecipe.execute.execute',
      [ os.path.join(site_perl_bin, 'notifier.pl'),
        mioga_conf_path ]
    )
    path_list.append(notifier_wrapper)

    searchengine_wrapper = self.createPythonScript(
      os.path.join(services_dir, 'searchengine'),
      'slapos.recipe.librecipe.execute.execute',
      [ os.path.join(site_perl_bin, 'searchengine.pl'),
        mioga_conf_path ]
    )
    path_list.append(searchengine_wrapper)

    crawl_fm = FileModifier( os.path.join('bin', 'search', 'crawl_sample.sh') )
    # TODO: The crawl script will still call the shell command "date"
    crawl_fm.modify(r'/var/tmp/crawl', self.options['log_dir'] + '/crawl')
    crawl_fm.modify(r'/var/lib/Mioga2/conf', mioga_base + '/conf')
    crawl_fm.modify(r'/usr/local/bin/(mioga2_(?:info|crawl|index).pl)', 
                    site_perl_bin + r"/\g<1>")
    crawl_path = os.path.join(self.options['bin_dir'], 'crawl.sh')
    crawl_fm.save(crawl_path)
    os.chmod(crawl_path, stat.S_IRWXU)

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



# Copied and adapted from mioga-hooks.py - how to reuse code?
class FileModifier:
  def __init__(self, filename):
    self.filename = filename
    f = open(filename, 'rb')
    self.content = f.read()
    f.close()
  
  def modifyParameter(self, key, value):
    (self.content, count) = re.subn(
      r'(<parameter[^>]*\sname\s*=\s*"' + re.escape(key) + r'"[^>]*\sdefault\s*=\s*")[^"]*',
      r"\g<1>" + value,
      self.content)
    return count

  def modify(self, pattern, replacement):
    (self.content, count) = re.subn(pattern, replacement, self.content)
    return count
      
  def save(self, output=""):
    if output == "":
      output = self.filename
    f = open(output, 'w')
    f.write(self.content)
    f.close()
