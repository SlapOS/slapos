from setuptools import setup, find_packages
import os

name = "slapos.recipe.nosqltestbed"
version = '0.0.9'

def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=( read('README.txt')
                   + '\n' +
                   read('CHANGES.txt')
                 )

setup(
    name = name,
    version = version,
    description = "ZC Buildout recipe for the No SQL test bed",
    long_description=long_description,
    license = "GPLv3",
    keywords = "buildout nosqltestbed",
    classifiers=[
        "Framework :: Buildout :: Recipe",
        "Programming Language :: Python",
    ],
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    install_requires = [
      'zc.recipe.egg',
      'setuptools',
      'slapos.lib.recipe',
      ],
    namespace_packages = ['slapos', 'slapos.recipe'],
    entry_points = {'zc.buildout': ['default = %s:NoSQLTestBed' % name]},
    )
