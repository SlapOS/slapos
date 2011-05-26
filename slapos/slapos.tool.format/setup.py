# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os

name = 'slapos.tool.format'

def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description=(
        read('README.txt')
        + '\n' +
        read('CHANGES.txt')
    )

setup(
    name = name,
    version = '1.1-dev-2',
    description = "slapos - partitioning tools for servers",
    long_description=long_description,
    license = "GPLv3",
    keywords = "vifib server partitioning",
    include_package_data = True,
    packages = find_packages('src'),
    package_dir = {'':'src'},
    namespace_packages = ['slapos'],
    # slapgos use this to create a clean ouput
    install_requires = [
      'netaddr', # to play safely with IPv6 prefixes
      'netifaces', # to fetch information about network devices
      'setuptools', # namespace
      'slapos.slap', # for posting data to vifib master
      'xml_marshaller', # to generate data
    ],
    entry_points = """
    [console_scripts]
    slapformat = %s:main
    """ % name,
    )
