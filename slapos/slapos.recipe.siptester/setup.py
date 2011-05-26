from setuptools import setup, find_packages
import os

name = "slapos.recipe.siptester"
version = '0.0.25'

def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=( read('README.txt')
                   + '\n' +
                   read('CHANGES.txt')
                 )

setup(
  name = name,
  version = version,
  author = 'Romain Courteaud',
  author_email = 'romain@nexedi.com',
  description = 
    "zc.buildout recipe that instanciate a siptester",
  long_description = long_description,
  license = "GPL2",
  keywords = "siptester buildout",
  classifiers = [
    "Framework :: Buildout :: Recipe",
  ],

  package_dir = {'': 'src'},
  packages = find_packages('src'),
  namespace_packages = ['slapos', 'slapos.recipe'],
  include_package_data = True,
  install_requires = ['setuptools', 'slapos.lib.recipe'],
  entry_points = {'zc.buildout': ['default = %s:CallerRecipe' % name,
                                  'caller = %s:CallerRecipe' % name,
                                  'receiver = %s:ReceiverRecipe' % name,
                                  ]},
  )
