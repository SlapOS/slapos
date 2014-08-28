
# Provide POSIX information about the user
# that is currently running buildout

import grp
import os
import pwd

from slapos.recipe.librecipe import GenericBaseRecipe                                                                                                 

class Recipe(GenericBaseRecipe):

    def _options(self, options):
        pinfo = pwd.getpwuid(os.getuid())
        options['pw_name'] = pinfo.pw_name
        options['pw_uid'] = pinfo.pw_uid
        options['pw_gid'] = pinfo.pw_gid
        options['pw_dir'] = pinfo.pw_dir
        options['pw_shell'] = pinfo.pw_shell

        ginfo = grp.getgrgid(os.getgid())
        options['gr_name'] = ginfo.gr_name
        options['gr_gid'] = ginfo.gr_gid

    def install(self):
        return []

    update = install

