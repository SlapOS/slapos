# -*- coding: utf-8 -*-

"""
Recipe environment.

See http://pypi.python.org/pypi/collective.recipe.environment/
"""
import os
from slapos.recipe.librecipe import shlex

class Recipe(object):
    """zc.buildout recipe"""

    def __init__(self, buildout, name, options):
        self.options = options
        print 'To replicate the environment in a shell: --------'
        for key in options:
            print 'export %s=%s' % (key, shlex.quote(options[key]))
        print '-------------------------------------------------'
        os.environ.update(options)
        options.update(os.environ)

    def install(self):
        """Installer"""
        return tuple()

    update = install


