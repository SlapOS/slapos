from setuptools import setup, find_packages

name = "slapos.recipe.slaprunner"
version = '1.2-dev'


def read(name):
  return open(name).read()

long_description = (read('README.txt') + '\n' + read('CHANGES.txt'))
setup(
    name=name,
    version=version,
    description="ZC Buildout recipe for OSOE SlapOS training",
    long_description=long_description,
    license="GPLv3",
    keywords="buildout slapos recipe runner",
    classifiers=[
        "Framework :: Buildout :: Recipe",
        "Programming Language :: Python",
    ],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
      'setuptools',  # for namespacing
      'slapos.lib.recipe',  # uses internally
      'zc.recipe.egg',
      'zc.buildout',  # it is recipe
      ],
    namespace_packages=['slapos', 'slapos.recipe'],
    entry_points={'zc.buildout': ['default = %s:Recipe' % name]},
    )
