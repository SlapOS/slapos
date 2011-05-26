from setuptools import setup, find_packages

name = "slapos.recipe.proactive"
version = '1.0'

def read(name):
  return open(name).read()

long_description=( read('README.txt')
                   + '\n' +
                   read('CHANGES.txt')
                 )

setup(
    name = name,
    version = version,
    description = "ZC Buildout recipe for create an proactive instance",
    long_description = long_description,
    author = "Cedric de Saint Martin",
    author_email = "cedric.dsm@tiolive.com",
    url = "http://www.slapos.org",
    license = "GPLv3",
    keywords = "buildout slapos proactive",
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
    entry_points = {'zc.buildout': ['default = %s:Recipe' % name]},
    )
