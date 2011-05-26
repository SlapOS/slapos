from setuptools import setup, find_packages
import os

name = "slapos.tool.proxy"
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
    description = "slapproxy - the slapos master proxy",
    long_description=long_description,
    license = "GPLv3",
    keywords = "vifib proxy slap",
    classifiers=[
      ],
    packages = find_packages('src'),
    include_package_data = True,
    package_dir = {'':'src'},
    namespace_packages = ['slapos', 'slapos.tool'],
    install_requires = [
      'Flask', # used to create this
      'lxml', # needed to play with XML trees
      'setuptools', # namespaces
      'slapos.slap', # slapgrid uses slap to communicate with vifib
      'xml_marshaller', # to unmarshall/marshall python objects to/from XML
    ],
    zip_safe=False,
    entry_points = """
    [console_scripts]
    slapproxy = %(name)s:main
    """ % dict(name=name),
    )
