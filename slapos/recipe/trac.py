# -*- coding: utf-8 -*-
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
import sys
import subprocess
import shutil
import json

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

  def __init__(self, buildout, name, options):

    pythonPath = ""

    for eggs in options['eggs-dirs'].splitlines():
      if eggs:
        for item in os.listdir(eggs):
          path = os.path.join(eggs, item)
          pythonPath = path + ":" + pythonPath

    options['python_path'] = pythonPath
    options['wsgi-dir'] = os.path.join(options['site-dir'].strip(), 'apache')
    options['git-dir'] = os.path.join(options['site-dir'].strip(), 'git')
    options['svn-dir'] = os.path.join(options['site-dir'].strip(), 'svn')
    return GenericBaseRecipe.__init__(self, buildout, name, options)

  def install(self):
    install_path = []

    env = os.environ
    env['LD_LIBRARY_PATH'] = self.options['python-lib']
    project_dir = self.options['site-dir'].strip()
    trac_admin = self.options['trac-admin'].strip()
    admin = self.options['admin-user'].strip()
    passwd = self.options['admin-password'].strip()
    config = os.path.join(project_dir, 'conf/trac.ini')
    filestat = self.options['file-status'].strip()
    self.logger.info("Checking if trac project is not installed...")
    if os.path.exists(filestat):
      os.unlink(filestat)
    if not os.path.exists(project_dir):
      self.logger.info("Starting trac project installation at %s" % project_dir)
      trac_args = [trac_admin, project_dir, 'initenv']
      db_string = "mysql://%s:%s@%s:%s/%s" % (
                  self.options['mysql-username'].strip(),
                  self.options['mysql-password'].strip(),
                  self.options['mysql-host'].strip(),
                  self.options['mysql-port'].strip(),
                  self.options['mysql-database'].strip()
      )
      process_install = subprocess.Popen(trac_args, stdout=subprocess.PIPE,
              stdin=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
      process_install.stdin.write('%s\n%s\n' % (self.options['project'].strip(),
                                            db_string))
      result = process_install.communicate()[0]
      process_install.stdin.close()
      if process_install.returncode is None or process_install.returncode != 0:
        if os.path.exists(project_dir):
          shutil.rmtree(project_dir)
        self.logger.error("Failed to initialize Trac.\nThe error was: %s" % result)
        return []
      os.mkdir(self.options['git-dir'])
      os.mkdir(self.options['svn-dir'])
      os.mkdir(self.options['wsgi-dir'])
      os.unlink(config)
      shutil.copy(self.options['trac-ini'].strip(), config)
      shutil.copy(self.options['trac-wsgi'].strip(),
                      os.path.join(self.options['wsgi-dir'], 'trac.wsgi'))
    else:
      self.logger.info("The directory %s already exist, skip project installation"
                      % project_dir)
      trac_args = [trac_admin, project_dir, 'repository', 'list']
      process_upgrade = subprocess.Popen(trac_args, stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT)
      result = process_upgrade.communicate()[0]
      if process_upgrade.returncode is None or process_upgrade.returncode != 0:
        self.logger.error("Failed to run Trac.\nThe error was: %s" % result)
        return []

    #Add All grant to admin user
    self.logger.info("Granting admin rights to the admin user.")
    trac_grant = [trac_admin, project_dir, "permission add %s TRAC_ADMIN" % admin]
    process = subprocess.Popen(trac_grant, stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT, env=env)
    result = process.communicate()[0]
    if process.returncode is None or process.returncode != 0:
      raise Exception("Failed to execute Trac-admin.\nThe error was: %s" % result)

    self.logger.info("Copying additional plugins into plugins directory")
    plugins_dir = os.path.join(project_dir, "plugins")
    for item in os.listdir(self.options['plugins-egg-dir'].strip()):
      source = os.path.join(self.options['plugins-egg-dir'].strip(), item)
      destination = os.path.join(plugins_dir, item)
      if not os.path.exists(destination):
        shutil.copytree(source, destination)

    svn_list = json.loads(self.options.get('svn-project-list', '{}'))
    for svn_repo in svn_list:
      svn_repo_path = os.path.join(self.options['svn-dir'], svn_repo)
      if not os.path.exists(svn_repo_path):
        self.logger.info("Initializing %s SVN repository..." % svn_repo)
        svn_args = [self.options['svn-repo-script'], project_dir,
                    svn_repo, svn_list[svn_repo]]
        process = subprocess.Popen(svn_args, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        result = process.communicate()[0]
        if process.returncode is None or process.returncode != 0:
          shutil.rmtree(svn_repo_path)
          raise Exception("Failed to create repository.\nThe error was: %s" % result)
        shutil.copy(self.options['trac-svn-hook'].strip(),
                      os.path.join(svn_repo_path, 'hooks/post-commit'))
        shutil.copy(self.options['post-revprop-change'].strip(),
                      os.path.join(svn_repo_path, 'hooks/post-revprop-change'))
        self.logger.info("Finished initializing %s reposiroty" % svn_repo)

    repolist = json.loads(self.options.get('git-project-list', '{}'))
    for repo, desc in repolist.iteritems():
      absolute_path = os.path.join(self.options['git-dir'], '%s.git' % repo)
      if not os.path.exists(absolute_path):
        self.logger.info("Initializing %s GIT repository..." % repo)
        subprocess.check_call([self.options['git-binary'], 'init',
                    '--bare', absolute_path])
        subprocess.check_call([trac_admin, project_dir, 'repository',
                    'add', repo, absolute_path, 'git'], env=env)
        subprocess.check_call([trac_admin, project_dir, 'repository',
                    'resync', repo], env=env)
        # XXX: Hardcoded path
        shutil.copy(self.options['trac-git-hook'].strip(),
                      os.path.join(absolute_path, 'hooks/post-commit'))
        description_filename = os.path.join(absolute_path, 'description')
        with open(description_filename, 'w') as description_file:
          description_file.write(desc)

    user_list = json.loads(self.options.get('user-list', '{}'))
    fd = open(os.path.join(project_dir, 'svnpasswd'), 'w')
    fd.write("[users]\n%s = %s" % (admin, passwd))
    os.system("%s -cb %s %s %s" % (self.options['htpasswd'],
                                  self.options['passwd-file'],
                                  admin, passwd)
    )
    for user in user_list:
      self.logger.info("Creating or updating user %s ..." % user)
      user_args = [self.options['htpasswd'], '-b', self.options['passwd-file'],
                  user, user_list[user]]
      process = subprocess.Popen(user_args, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
      result = process.communicate()[0]
      if process.returncode is None or process.returncode != 0:
          raise Exception("Failed to create user %s.\nThe error was: %s" %
                          (user, result))
      fd.write("\n%s = %s" % (user, user_list[user]))
    fd.close()
    open(filestat, "w").write("done.")

    return install_path

