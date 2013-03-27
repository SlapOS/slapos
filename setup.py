from setuptools import setup, find_packages
import glob
import os

from slapos.version import version

name = 'slapos.core'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read() + "\n"

for f in sorted(glob.glob(os.path.join('slapos', 'README.*.txt'))):
  long_description += '\n' + open(f).read() + '\n'

additional_install_requires = []
# Even if argparse is available in python2.7, some python2.7 installations
# do not have it, so checking python version is dangerous
try:
  import argparse
except ImportError:
  additional_install_requires.append('argparse')

setup(name=name,
      version=version,
      description="SlapOS core.",
      long_description=long_description,
      classifiers=[
          "Programming Language :: Python",
        ],
      keywords='slapos core',
      license='GPLv3',
      url='http://www.slapos.org',
      author='VIFIB',
      namespace_packages=['slapos'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
          'Flask', # used by proxy
          'lxml', # needed to play with XML trees
          'netaddr>=0.7.5', # to play safely with IPv6 prefixes
          'netifaces', # to fetch information about network devices
          'setuptools', # namespaces
          'supervisor', # slapgrid uses supervisor to manage processes
          'xml_marshaller>=0.9.3', # to unmarshall/marshall python objects to/from
                                   # XML
          'zope.interface', # slap library implementes interfaces
          'zc.buildout',
        ] + additional_install_requires,
      extra_requires={'docs': ('Sphinx', 'repoze.sphinx.autointerface'),},
      tests_require=[
          'unittest2',
          'pyflakes',
      ],
      zip_safe=False, # proxy depends on Flask, which has issues with
                      # accessing templates
      entry_points={
        'console_scripts': [
          # One entry point to control them all
          'slapos = slapos.entry:main',
          'slapos-watchdog = slapos.grid.watchdog:main',
          'slapproxy = slapos.proxy:main',
          'slapproxy-query = slapos.proxy.query:main',
          # Deprecated entry points
          'slapconsole = slapos.client:slapconsole',
          'slapformat = slapos.format:main',
          'slapgrid = slapos.grid.slapgrid:run',
          'slapgrid-sr = slapos.grid.slapgrid:runSoftwareRelease',
          'slapgrid-cp = slapos.grid.slapgrid:runComputerPartition',
          'slapgrid-ur = slapos.grid.slapgrid:runUsageReport',
          'slapgrid-supervisorctl = slapos.grid.svcbackend:supervisorctl',
          'slapgrid-supervisord = slapos.grid.svcbackend:supervisord',
          'bang = slapos.bang:main',
        ]
      },
      test_suite="slapos.tests",
    )
