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
          'cliff',
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
          'slapos-watchdog = slapos.grid.watchdog:main',
          'slapproxy = slapos.cli_legacy.proxy:main',
          'slapproxy-query = slapos.proxy.query:main',
          'slapos = slapos.cli.entry:main',
          # Deprecated entry points
          'slapconsole = slapos.cli_legacy.console:console',
          'slapformat = slapos.cli_legacy.format:main',
          'slapgrid-sr = slapos.cli_legacy.slapgrid:runSoftwareRelease',
          'slapgrid-cp = slapos.cli_legacy.slapgrid:runComputerPartition',
          'slapgrid-ur = slapos.cli_legacy.slapgrid:runUsageReport',
          'slapgrid-supervisorctl = slapos.cli_legacy.svcbackend:supervisorctl',
          'slapgrid-supervisord = slapos.cli_legacy.svcbackend:supervisord',
          'bang = slapos.cli_legacy.bang:main',
        ],
        'slapos.cli': [
          'cache lookup = slapos.cli.cache:CacheLookupCommand',
          'node bang = slapos.cli.bang:BangCommand',
          'node format = slapos.cli.format:FormatCommand',
          'node register = slapos.cli.register:RegisterCommand',
          'node supervisord = slapos.cli.supervisord:SupervisordCommand',
          'node supervisorctl = slapos.cli.supervisorctl:SupervisorctlCommand',
          'node status = slapos.cli.supervisorctl:SupervisorctlStatusCommand',
          'node start = slapos.cli.supervisorctl:SupervisorctlStartCommand',
          'node stop = slapos.cli.supervisorctl:SupervisorctlStopCommand',
          'node restart = slapos.cli.supervisorctl:SupervisorctlRestartCommand',
          'node tail = slapos.cli.supervisorctl:SupervisorctlTailCommand',
          'node report = slapos.cli.slapgrid:ReportCommand',
          'node software = slapos.cli.slapgrid:SoftwareCommand',
          'node instance = slapos.cli.slapgrid:InstanceCommand',
          'console = slapos.cli.console:ConsoleCommand',
          'supply = slapos.cli.supply:SupplyCommand',
          'remove = slapos.cli.remove:RemoveCommand',
          'request = slapos.cli.request:RequestCommand',
        ]
      },
      test_suite="slapos.tests",
    )
