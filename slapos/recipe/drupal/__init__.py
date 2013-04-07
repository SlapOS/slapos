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
import re
import subprocess
import tempfile
import textwrap

from slapos.recipe.librecipe import GenericBaseRecipe


# XXX
# Current issues:
# - drush connects to mysql with the password on command line
#    see http://stackoverflow.com/questions/6607675/shell-script-password-security-of-command-line-parameters
#    it could use a socket, but we are on a different instance than mysql
# - using slapproxy, sometimes this recipe is not able to connect to mysql (tunnel down).
#   restarting from supervisor usually solves it.
#


def chown_set(path, mode):
    prev_mode = os.stat(path).st_mode
    os.chmod(path, prev_mode | mode)


class InitRecipe(GenericBaseRecipe):
    """\
    This recipe performs deployment steps for Drupal:

        - Call the 'drush' command to install a Drupal site and initial database schema.

    Database connection parameters are taken from the provided settings.php file.

    If the database is not empty (ie contains at least one table) the drush script is not called.

    """

    def install(self):
        drush_binary = self.options['drush-binary']
        htdocs = self.options['htdocs']

        settings_php = self.options['settings-php']
        if not settings_php.startswith('/'):
            settings_php = os.path.join(htdocs, settings_php)

        os.chdir(htdocs)

        if self.is_db_empty(php_binary=self.options['php-binary'],
                            settings_php=settings_php):

            subprocess.check_output([drush_binary,
                                     '-y', 'site-install',
                                     self.options['profile'],
                                     '--account-name=admin',
                                     '--account-pass=%s' % self.options['admin-password'],
                                     ],
                                     stderr=subprocess.STDOUT)

            # drush removes the 'w' bit from both the settings file and its
            # directory.
            # we restore them, otherwise buildout will see the file as changed
            # and try to remove it and reinstall the apachephp recipe.

            for path in [settings_php, os.path.dirname(settings_php)]:
                chown_set(path, 0200)

        # XXX return what?
        return []


    def is_db_empty(self, php_binary, settings_php):
        with tempfile.NamedTemporaryFile() as fout:
            settings_dirname, settings_filename = os.path.split(settings_php)
            fout.write(textwrap.dedent("""\
                #!%(php_binary)s
                <?php

                ini_set('include_path',ini_get('include_path').':%(settings_dirname)s:');
                require('%(settings_filename)s');

                # taken from drupal: includes/mysql/database.inc
                $connection_options = $databases['default']['default'];

                $dsn = 'mysql:host=' . $connection_options['host'] . ';port=' . (empty($connection_options['port']) ? 3306 : $connection_options['port']);
                $dsn .= ';dbname=' . $connection_options['database'];

                $db = new PDO($dsn, $connection_options['username'], $connection_options['password']);

                $tables = $db->query('SHOW TABLES')->fetchAll();

                if (count($tables) > 0) {
                    exit(10);
                } else {
                    exit(0);
                }
                """ % {
                    'php_binary': php_binary,
                    'settings_dirname': settings_dirname,
                    'settings_filename': settings_filename
                    }))
            fout.flush()

            try:
                output = subprocess.check_call([php_binary, '-f', fout.name])
            except subprocess.CalledProcessError as exc:
                if exc.returncode == 10:
                    # the database already contains some tables.
                    return False

        return True




