from setuptools import setup, find_packages
import os

name = "slapos.tool.grid"
version = '1.1-dev-2'

def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=(
        read('README.txt')
        + '\n' +
        read('CHANGES.txt')
    )

additional_install_requires = []

# Even if argparse is available in python2.7, some python2.7 installations
# do not have it, so checking python version is dangerous
try:
  import argparse
except ImportError:
  additional_install_requires.append('argparse')

setup(
    name = name,
    version = version,
    description = "slapgrid - the vifib client with proposals server cannot"\
        " refuse",
    long_description=long_description,
    license = "GPLv3",
    keywords = "vifib server installation",
    classifiers=[
      ],
    packages = find_packages('src'),
    include_package_data = True,
    package_dir = {'':'src'},
    namespace_packages = [ 'slapos' ],
    install_requires = [
      'setuptools', # namespaces
      'zc.buildout>=1.5.0', # slapgrid uses buildout as its backend to do the job
      'slapos.slap', # slapgrid uses slap to communicate with vifib
      'supervisor', # slapgrid uses supervisor to manage processes
    ] + additional_install_requires,
    zip_safe=False,
    entry_points = """
    [console_scripts]
    slapgrid = %(name)s.slapgrid:run
    slapgrid-sr = %(name)s.slapgrid:runSoftwareRelease
    slapgrid-cp = %(name)s.slapgrid:runComputerPartition
    slapgrid-ur = %(name)s.slapgrid:runUsageReport
    slapgrid-supervisorctl = %(name)s.svcbackend:supervisorctl
    slapgrid-supervisord = %(name)s.svcbackend:supervisord
    """ % dict(name=name),
    )
