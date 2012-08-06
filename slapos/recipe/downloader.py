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
import urllib
import hashlib

from slapos.recipe.librecipe import GenericBaseRecipe

BUFFER_SIZE = 1024

def service(args):
    if not os.path.exists(args['confirm']):
        urllib.urlretrieve(args['url'], args['output'])

        if args['md5'] is not None:
            # XXX: Find a better way to do a md5sum
            md5sum = hashlib.md5()
            with open(args['output'], 'r') as output:
                file_buffer = output.read(BUFFER_SIZE)
                while len(file_buffer) > 0:
                    md5sum.update(file_buffer)
                    file_buffer = output.read(BUFFER_SIZE)

            if args['md5'] != md5sum.hexdigest():
                return 127 # Not-null return code

        # Just a touch on args['confirm'] file
        open(args['confirm'], 'w').close()

    return 0



class Recipe(GenericBaseRecipe):

    def install(self):
        path_list = []

        md5sum = self.options.get('md5sum', '')
        if len(md5sum) == 0:
            md5sum = None

        path_list.append(
            self.createPythonScript(
                self.options['binary'],
                'slapos.recipe.downloader.service',
                {
                    'url': self.options['url'],
                    'md5': md5sum,
                    'output': self.options['downloaded-file'],
                    'confirm': self.options['downloaded-file-complete']
                }
            )
        )

        return path_list
