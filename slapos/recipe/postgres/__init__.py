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
import shutil
from zc.buildout import UserError

from slapos.recipe.librecipe import GenericBaseRecipe



class Recipe(GenericBaseRecipe):
    """\
    This recipe creates:

        - a Postgres cluster
        - configuration to allow connections from IPv4, IPv6 or unix socket.
        - a superuser with provided name and generated password
        - a database with provided name
        - a start script in the services directory

    Required options:
        bin
            path to the 'initdb' and 'postgres' binaries.
        dbname
            name of the database to be used by the application.
        ipv4
            set of ipv4 to listen on.
        ipv6
            set of ipv6 to listen on.
        pgdata-directory
            path to postgres configuration and data.
        services
            must be ${buildout:directory}/etc/service.
        superuser
            name of the superuser to create.

    Exposed options:
        password
            generated password for the superuser.
        url
            generated DBAPI connection string.
            it can be used as-is (ie. in sqlalchemy) or by the _urlparse.py recipe.
    """

    def _options(self, options):
        options['url'] = 'postgresql://%(superuser)s:%(password)s@[%(ipv6-random)s]:%(port)s/%(dbname)s' % options


    def install(self):
        pgdata = self.options['pgdata-directory']

        # if the pgdata already exists, skip all steps, we don't need to do anything.

        if not os.path.exists(pgdata):
            try:
                self.createCluster()
                self.createConfig()
                self.createDatabase()
                self.updateSuperuser()
                self.createRunScript()
            except:
                # do not leave half-installed postgresql - else next time we
                # run we won't update it.
                shutil.rmtree(pgdata)
                raise



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

        Here we create an empty cluster.
        """
        initdb_binary = os.path.join(self.options['bin'], 'initdb')
        self.check_exists(initdb_binary)

        pgdata = self.options['pgdata-directory']

        try:
            subprocess.check_call([initdb_binary,
                                   '-D', pgdata,
                                   '-A', 'ident',
                                   '-E', 'UTF8',
                                   '-U', self.options['superuser'],
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
            # see http://www.postgresql.org/docs/9.2/static/auth-pg-hba-conf.html

            cfg_lines = [
                '# TYPE  DATABASE        USER            ADDRESS                 METHOD',
                '',
                '# "local" is for Unix domain socket connections only (check unix_socket_permissions!)',
                'local   all             all                                     trust',
                'host    all             all             127.0.0.1/32            md5',
                'host    all             all             ::1/128                 md5',
            ]

            ipv4_netmask_bits = self.options.get('ipv4-netmask-bits', '32')
            for ip in ipv4:
                cfg_lines.append('host    all             all             %s/%s                   md5' % (ip, ipv4_netmask_bits))

            ipv6_netmask_bits = self.options.get('ipv6-netmask-bits', '128')
            for ip in ipv6:
                cfg_lines.append('host    all             all             %s/%s                   md5' % (ip, ipv6_netmask_bits))

            cfg.write('\n'.join(cfg_lines))


    def createDatabase(self):
        self.runPostgresCommand(cmd='CREATE DATABASE "%s"' % self.options['dbname'])


    def updateSuperuser(self):
        """\
        Set a password for the cluster administrator.
        The application will also use it for its connections.
        """

        # http://postgresql.1045698.n5.nabble.com/Algorithm-for-generating-md5-encrypted-password-not-found-in-documentation-td4919082.html

        user = self.options['superuser']
        password = self.options['password']

        # encrypt the password to avoid storing in the logs
        enc_password = 'md5' + md5.md5(password+user).hexdigest()

        self.runPostgresCommand(cmd="""ALTER USER "%s" ENCRYPTED PASSWORD '%s'""" % (user, enc_password))


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


