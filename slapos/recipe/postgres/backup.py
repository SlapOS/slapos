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

import textwrap

from slapos.recipe.librecipe import GenericBaseRecipe



class ExportRecipe(GenericBaseRecipe):
    """\
    This recipe creates an exporter script for using with the resilient stack.

    Required options:
        backup-directory
            folder that will contain the dump file.
        bin
            path to the 'pg_dump' binary.
        dbname
            name of the database to dump.
        pgdata-directory
            path to postgres configuration and data.
        wrapper
            full path of the exporter script to create.
    """

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
                        --username postgres \\
                        --format=custom \\
                        --file=%(backup-directory)s/database.dump \\
                        %(dbname)s
                """ % self.options)
        self.createExecutable(wrapper, content=content)



class ImportRecipe(GenericBaseRecipe):
    """\
    This recipe creates an importer script for using with the resilient stack.

    Required options:
        backup-directory
            folder that contains the dump file.
        bin
            path to the 'pg_restore' binary.
        dbname
            name of the database to restore.
        pgdata-directory
            path to postgres configuration and data.
        wrapper
            full path of the importer script to create.
    """

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
                        --username postgres \\
                        --dbname=%(dbname)s \\
                        --clean \\
                        --no-owner \\
                        --no-acl \\
                        %(backup-directory)s/database.dump
                """ % self.options)
        self.createExecutable(wrapper, content=content)


