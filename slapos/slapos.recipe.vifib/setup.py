from setuptools import setup, find_packages

name = "slapos.recipe.vifib"
version = '1.1.dev-8'

def read(name):
  return open(name).read()

long_description=( read('README.txt')
                   + '\n' +
                   read('CHANGES.txt')
                 )

setup(
    name = name,
    version = version,
    description = "ZC Buildout recipe for create a Vifib instance",
    long_description=long_description,
    license = "GPLv3",
    keywords = "buildout slapos vifib",
    classifiers=[
        "Framework :: Buildout :: Recipe",
        "Programming Language :: Python",
    ],
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    install_requires = [
      'setuptools', # for namespacing
      'slapos.recipe.erp5', # reuses logic
      'zc.buildout', # it is recipe
      ],
    namespace_packages = ['slapos', 'slapos.recipe'],
    entry_points = {'zc.buildout': ['default = %s:Recipe' % name]},
    )
