from setuptools import setup, find_packages
import os

name = "slapos.tool.console"
version = '1.1-dev'

def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=(
        read('README.txt')
        + '\n' +
        read('CHANGES.txt')
    )

setup(
    name = name,
    version = version,
    description = "slapconsole - the slap library console",
    long_description=long_description,
    license = "GPLv3",
    keywords = "vifib console slap",
    classifiers=[
      ],
    packages = find_packages('src'),
    include_package_data = True,
    package_dir = {'':'src'},
    namespace_packages = ['slapos', 'slapos.tool'],
    install_requires = [
      'setuptools', # namespaces
      'slapos.slap', # slapgrid uses slap to communicate with vifib
    ],
    zip_safe=False,
    entry_points = """
    [console_scripts]
    slapconsole = %(name)s.console:run
    """ % dict(name=name),
    )
