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
import json
import os

from subprocess import check_call

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):

    def install(self):

        repolist = json.loads(self.options['repos'])
        for repo, desc in repolist.iteritems():
            absolute_path = os.path.join(self.options['base-directory'], '%s.git' % repo)
            if not os.path.exists(absolute_path):
                check_call([self.options['git-binary'], 'init',
                            '--bare', absolute_path])
                # XXX: Hardcoded path
                description_filename = os.path.join(absolute_path, 'description')
                with open(description_filename, 'w') as description_file:
                    description_file.write(desc)

        return []
