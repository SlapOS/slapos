##############################################################################
#
# Copyright (c) 2013 Vifib SARL and Contributors. All Rights Reserved.
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
        srv-directory
            folder that contain the runner directory.
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
                #!%(shell-binary)s
                umask 077
                sync_element () {
                  path=$1
                  backup_path=$2
                  shift 2
                  element_list=$*
                  for element in $element_list
                  do
                    cd $path;
                    if [ -f $element ] || [ -d $element ]; then
                       %(rsync-binary)s -avz --safe-links $element  $backup_path;
                    fi
                  done
                }
                sync_element %(srv-directory)s/runner  %(backup-directory)s/runner/ instance project  proxy.db softwareLink
                sync_element %(etc-directory)s  %(backup-directory)s/etc/ .rcode .project .users
                if [ -d %(backup-directory)s/runner/software ]; then
                  rm %(backup-directory)s/runner/software/*
                fi
                """ % self.options)
        self.createExecutable(wrapper, content=content)



class ImportRecipe(GenericBaseRecipe):
    """\
    This recipe creates an importer script for using with the resilient stack.

    Required options:
        backup-directory
            folder that will contain the dump file.
        srv-directory
            folder that contain the runner directory.
        wrapper
            full path of the exporter script to create.
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
                #!%(shell-binary)s
                umask 077
                cd %(backup-directory)s;
                %(rsync-binary)s -avz runner/  %(srv-directory)s/runner;
                %(rsync-binary)s -avz etc/ %(etc-directory)s;
                ifs=$IFS IFS=';'
                read user pass remaining < %(etc-directory)s/.users
                IFS=$ifs
                %(curl-binary)s -vg6L -F clogin="$user" -F cpwd="$pass" --dump-header login_cookie  %(backend-url)s/doLogin;
                %(curl-binary)s -vg6LX POST --cookie login_cookie --max-time 5  %(backend-url)s/runSoftwareProfile;
                rm -f login_cookie
                """ % self.options)
        self.createExecutable(wrapper, content=content)


