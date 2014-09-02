import grp
import os
import pwd

class Recipe(object):
    """
    Provide POSIX information about the user that is currently running buildout.
    """

    def __init__(self, buildout, name, options):
        pinfo = pwd.getpwuid(os.getuid())
        options['pw-name'] = pinfo.pw_name
        options['pw-uid'] = pinfo.pw_uid
        options['pw-gid'] = pinfo.pw_gid
        options['pw-dir'] = pinfo.pw_dir
        options['pw-shell'] = pinfo.pw_shell

        ginfo = grp.getgrgid(os.getgid())
        options['gr-name'] = ginfo.gr_name
        options['gr-gid'] = ginfo.gr_gid

    install = update = lambda self: []
