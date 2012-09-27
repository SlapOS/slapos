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

import ConfigParser
import errno
import lxml.etree
import md5
import os

import lxml


# TODO: remove the hack below, used to reach psycopg2
# XXX: When run inside webrunner, Postgres refuses connection.
# TODO: make the recipe work inside webrunner



def temporary_hack():
    # XXX TODO provide psycopg to sys.path by other means
    import sys
    develop_eggs = '/'.join(lxml.__file__.split('/')[:lxml.__file__.split('/').index('develop-eggs')+1])
    for egg_folder in os.listdir(develop_eggs):
        if egg_folder.startswith('psycopg2'):
            sys.path.append(os.path.join(develop_eggs, egg_folder))
temporary_hack()

import psycopg2

from slapos.recipe.librecipe import GenericBaseRecipe


def xpath_set(xml, settings):
    for path, value in settings.iteritems():
        xml.xpath(path)[0].text = value


class Recipe(GenericBaseRecipe):
    """\
    This recipe configures a maarch instance to be ready to run,
    without going through the initial wizard:

     - creation of two xml files from the provided defaults
     - php.ini as required by Maarch
     - database setup.

     The superuser password will be the same as the Postgres one.
    """

    def install(self):
        apps_config_xml = self.create_apps_config_xml()
        core_config_xml = self.create_core_config_xml()

        self.update_phpini(php_ini_path=os.path.join(self.options['php_ini_dir'], 'php.ini'))

        self.load_initial_db()

        # confirm that everything is done, the app will run without further setup
        lck_path = self.installed_lock()

        return [
                apps_config_xml,
                core_config_xml,
                lck_path,
                ]


    def create_apps_config_xml(self):
        options = self.options

        folder = os.path.join(options['htdocs'], 'apps/maarch_entreprise/xml')
        config_xml_default = os.path.join(folder, 'config.xml.default')
        config_xml = os.path.join(folder, 'config.xml')

        # do not overwrite the config.xml file (it can be customized inside the application)
        if os.path.exists(config_xml):
            return

        content = open(config_xml_default, 'rb').read()
        xml = lxml.etree.fromstring(content)

        xpath_set(xml, {
            'CONFIG/databaseserver': options['db_host'],
            'CONFIG/databaseserverport': options['db_port'],
            'CONFIG/databasename': options['db_dbname'],
            'CONFIG/databaseuser': options['db_username'],
            'CONFIG/databasepassword': options['db_password'],
            'CONFIG/lang': options['language'],
            })

        with os.fdopen(os.open(config_xml, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600), 'w') as fout:
            fout.write(lxml.etree.tostring(xml, xml_declaration=True, encoding='utf-8').encode('utf-8'))

        return config_xml


    def create_core_config_xml(self):
        options = self.options

        folder = os.path.join(options['htdocs'], 'core/xml')
        config_xml_default = os.path.join(folder, 'config.xml.default')
        config_xml = os.path.join(folder, 'config.xml')

        # do not overwrite the config.xml file (it can be customized inside the application)
        if os.path.exists(config_xml):
            return

        content = open(config_xml_default, 'rb').read()
        xml = lxml.etree.fromstring(content)

        xpath_set(xml, {
            'CONFIG/defaultlanguage': options['language'],
            })

        with os.fdopen(os.open(config_xml, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600), 'w') as fout:
            fout.write(lxml.etree.tostring(xml, xml_declaration=True, encoding='utf-8').encode('utf-8'))

        return config_xml


    def update_phpini(self, php_ini_path):
        php_ini = ConfigParser.RawConfigParser()
        php_ini.read(php_ini_path)

        php_ini.set('PHP', 'error_reporting', 'E_ALL & ~E_DEPRECATED & ~E_NOTICE')
        php_ini.set('PHP', 'display_errors', 'On')
        php_ini.set('PHP', 'short_open_tag', 'On')
        php_ini.set('PHP', 'magic_quotes_gpc', 'Off')

        with os.fdopen(os.open(php_ini_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600), 'w') as fout:
            php_ini.write(fout)


    def load_initial_db(self):
        """
        This method:

         - creates the initial schema
         - patches the schema for ipv6
         - loads initial data
         - sets initial superadmin password
         - configures and creates docservers directories
        """

        options = self.options

        conn = psycopg2.connect(host = options['db_host'],
                                port = int(options['db_port']),
                                database = options['db_dbname'],
                                user = options['db_username'],
                                password = options['db_password'])

        cur = conn.cursor()

        # skip everything if the tables have already been created
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='docservers';")
        if cur.rowcount == 1:
            conn.close()
            return

        htdocs = options['htdocs']

        # load the schema
        with open(os.path.join(htdocs, 'structure.sql')) as fin:
            cur.execute(fin.read())

        # patch the schema to store long addresses (ipv6)
        cur.execute('ALTER TABLE HISTORY ALTER COLUMN remote_ip TYPE CHAR(255);')

        with open(os.path.join(htdocs, 'data_mini.sql')) as fin:
            cur.execute(fin.read())

        # initial admin password
        enc_password = md5.md5(options['db_password']).hexdigest()
        cur.execute("UPDATE users SET password=%s WHERE user_id='superadmin';", (enc_password, ))

        # directories described in http://wiki.maarch.org/Maarch_Entreprise/fr/Man/Admin/Stockage
        for docserver_id, foldername in [
                ('OFFLINE_1', 'offline'),
                ('FASTHD_AI', 'ai'),
                ('OAIS_MAIN_1', 'OAIS_main'),
                ('OAIS_SAFE_1', 'OAIS_safe'),
                ('FASTHD_MAN', 'manual'),
                ('TEMPLATES', 'templates'),
                ]:
            full_path = os.path.join(self.options['root_docservers'], foldername)
            cur.execute('UPDATE docservers SET path_template=%s WHERE docserver_id=%s', (full_path, docserver_id))
            try:
                os.makedirs(full_path)
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    pass
                else:
                    raise

        conn.commit()
        cur.close()
        conn.close()


    def installed_lock(self):
        """\
        Create an empty file to mean the setup is completed
        """
        htdocs = self.options['htdocs']
        lck_path = os.path.join(htdocs, 'installed.lck')

        with open(lck_path, 'w'):
            pass

        return lck_path


