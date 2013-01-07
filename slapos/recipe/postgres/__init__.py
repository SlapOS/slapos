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

import md5
import os
import subprocess
import textwrap
from zc.buildout import UserError

from slapos.recipe.librecipe import GenericBaseRecipe



class Recipe(GenericBaseRecipe):
    """\
    This recipe creates:

        - a Postgres cluster
        - configuration to allow connections from IPv4, IPv6 or unix socket.
        - a superuser with provided name and generated password
        - a database with provided name
        - a foreground start script in the services directory

    then adds the connection URL to the options.
    The URL can be used as-is (ie. in sqlalchemy) or by the _urlparse.py recipe.
    """

    def _options(self, options):
        options['password'] = self.generatePassword()
        options['url'] = 'postgresql://%(user)s:%(password)s@[%(ipv6_random)s]:%(port)s/%(dbname)s' % options


    def install(self):
        pgdata = self.options['pgdata-directory']

        # if the pgdata already exists, skip all steps, we don't need to do anything.

        if not os.path.exists(pgdata):
            self.createCluster()
            self.createConfig()
            self.createDatabase()
            self.createSuperuser()
            self.createRunScript()

        # install() methods usually return the pathnames of managed files.
        # If they are missing, they will be rebuilt.
        # In this case, we already check for the existence of pgdata,
        # so we don't need to return anything here.

        return []


    def check_exists(self, path):
        if not os.path.isfile(path):
            raise IOError('File not found: %s' % path)


    def createCluster(self):
        """\
        A Postgres cluster is "a collection of databases that is managed
        by a single instance of a running database server".

        Here we create an empty cluster. The authentication for this
        command is through the unix socket.
        """
        initdb_binary = os.path.join(self.options['bin'], 'initdb')
        self.check_exists(initdb_binary)

        pgdata = self.options['pgdata-directory']

        try:
            subprocess.check_call([initdb_binary,
                                   '-D', pgdata,
                                   '-A', 'ident',
                                   '-E', 'UTF8',
                                   ])
        except subprocess.CalledProcessError:
            raise UserError('Could not create cluster directory in %s' % pgdata)


    def createConfig(self):
        pgdata = self.options['pgdata-directory']
        ipv4 = self.options['ipv4']
        ipv6 = self.options['ipv6']

        with open(os.path.join(pgdata, 'postgresql.conf'), 'wb') as cfg:
            cfg.write(textwrap.dedent("""\
                    listen_addresses = '%s'
                    logging_collector = on
                    log_rotation_size = 50MB
                    max_connections = 100
                    datestyle = 'iso, mdy'

                    lc_messages = 'en_US.UTF-8'
                    lc_monetary = 'en_US.UTF-8'
                    lc_numeric = 'en_US.UTF-8'
                    lc_time = 'en_US.UTF-8'
                    default_text_search_config = 'pg_catalog.english'

                    unix_socket_directory = '%s'
                    unix_socket_permissions = 0700
                    """ % (
                        ','.join(ipv4.union(ipv6)),
                        pgdata,
                        )))

        with open(os.path.join(pgdata, 'pg_hba.conf'), 'wb') as cfg:
            # see http://www.postgresql.org/docs/9.1/static/auth-pg-hba-conf.html

            cfg_lines = [
                '# TYPE  DATABASE        USER            ADDRESS                 METHOD',
                '',
                '# "local" is for Unix domain socket connections only (check unix_socket_permissions!)',
                'local   all             all                                     ident',
                'host    all             all             127.0.0.1/32            md5',
                'host    all             all             ::1/128                 md5',
            ]

            for ip in ipv4:
                cfg_lines.append('host    all             all             %s/32                   md5' % ip)

            for ip in ipv6:
                cfg_lines.append('host    all             all             %s/128                   md5' % ip)

            cfg.write('\n'.join(cfg_lines))


    def createDatabase(self):
        self.runPostgresCommand(cmd='CREATE DATABASE "%s"' % self.options['dbname'])


    def createSuperuser(self):
        """\
        Creates a Postgres superuser - other than "slapuser#" for use by the application.
        """

        # http://postgresql.1045698.n5.nabble.com/Algorithm-for-generating-md5-encrypted-password-not-found-in-documentation-td4919082.html

        user = self.options['user']
        password = self.options['password']

        # encrypt the password to avoid storing in the logs
        enc_password = 'md5' + md5.md5(password+user).hexdigest()

        self.runPostgresCommand(cmd="""CREATE USER "%s" ENCRYPTED PASSWORD '%s' SUPERUSER""" % (user, enc_password))


    def runPostgresCommand(self, cmd):
        """\
        Executes a command in single-user mode, with no daemon running.

        Multiple commands can be executed by providing newlines,
        preceeded by backslash, between them.
        See http://www.postgresql.org/docs/9.1/static/app-postgres.html
        """

        pgdata = self.options['pgdata-directory']
        postgres_binary = os.path.join(self.options['bin'], 'postgres')

        try:
            p = subprocess.Popen([postgres_binary,
                                  '--single',
                                  '-D', pgdata,
                                  'postgres',
                                  ], stdin=subprocess.PIPE)

            p.communicate(cmd+'\n')
        except subprocess.CalledProcessError:
            raise UserError('Could not create database %s' % pgdata)


    def createRunScript(self):
        """\
        Creates a script that runs postgres in the foreground.
        'exec' is used to allow easy control by supervisor.
        """
        content = textwrap.dedent("""\
                #!/bin/sh
                exec %(bin)s/postgres \\
                    -D %(pgdata-directory)s
                """ % self.options)
        name = os.path.join(self.options['services'], 'postgres-start')
        self.createExecutable(name, content=content)



class ExportRecipe(GenericBaseRecipe):

    def install(self):
        wrapper = self.options['wrapper']
        self.createBackupScript(wrapper)
        return [wrapper]


    def createBackupScript(self, wrapper):
        """\
        Create a script to backup the database in 'custom' format.
        """
        content = textwrap.dedent("""\
                #!/bin/sh
                umask 077
                %(bin)s/pg_dump \\
                        --host=%(pgdata-directory)s \\
                        --format=custom \\
                        --file=%(backup-directory)s/database.dump \\
                        %(dbname)s
                """ % self.options)
        self.createExecutable(wrapper, content=content)



class ImportRecipe(GenericBaseRecipe):

    def install(self):
        wrapper = self.options['wrapper']
        self.createRestoreScript(wrapper)
        return [wrapper]


    def createRestoreScript(self, wrapper):
        """\
        Create a script to restore the database from 'custom' format.
        """
        content = textwrap.dedent("""\
                #!/bin/sh
                %(bin)s/pg_restore \\
                        --host=%(pgdata-directory)s \\
                        --dbname=%(dbname)s \\
                        --clean \\
                        --no-owner \\
                        --no-acl \\
                        %(backup-directory)s/database.dump
                """ % self.options)
        self.createExecutable(wrapper, content=content)


