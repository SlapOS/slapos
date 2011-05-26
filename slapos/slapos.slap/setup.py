from setuptools import setup, find_packages

name="slapos.slap"
version='1.2'

def read(name):
  return open(name).read()

long_description=(
  read('README.txt')
  + '\n' +
  read('CHANGES.txt')
)

setup(
  name=name,
  version=version,
  description="slap - Simple Language for Accounting and Provisioning"
    " python library",
  long_description=long_description,
  license="GPLv3",
  keywords="slap library",
  classifiers=[
    ],
  py_modules = ["slapos.slap.interface.slap"],
  namespace_packages = ['slapos'],
  packages=find_packages('src'),
  include_package_data=True,
  package_dir={'':'src'},
  install_requires=[
    'lxml',
    'setuptools',
    'xml_marshaller>=0.9.3',
    'zope.interface',
    ],
  zip_safe=True,
)
