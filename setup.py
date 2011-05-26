from setuptools import setup, find_packages
import glob
import os

version = '0.1'
name = 'slapos.recipebox'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read() + "\n"

for f in glob.glob(os.path.join('slapos', 'recipe', 'README.*.txt')):
  subname = os.path.basename(f)
  long_description += subname + '\n' + '=' * len(subname) + '\n\n' \
    + open(f).read() + '\n'

# extras_requires are not used because of
#   https://bugs.launchpad.net/zc.buildout/+bug/85604
setup(name=name,
      version=version,
      description="Box full of slapos recipes.",
      long_description=long_description,
      classifiers=[
          "Framework :: Buildout :: Recipe",
          "Programming Language :: Python",
        ],
      keywords='slapos recipe box',
      license='GPLv3',
      namespace_packages=['slapos', 'slapos.recipe'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
        'setuptools', # for namespace and internal usage
        'zc.buildout', # needed to play internally
        'PyXML', # for full blown python interpreter
        'lxml', # for full blown python interpreter
        'xml_marshaller', # need to communication with slapgrid
        'slapos.lib.recipe', # makes instantiation recipes simpler
        'zc.recipe.egg', # allows to generate scripts
        ],
      zip_safe=True,
      entry_points={
        'zc.buildout': [
          'build = slapos.recipe.build:Script',
          'buildcmmi = slapos.recipe.build:Cmmi',
          'erp5testnode = slapos.recipe.erp5testnode:Recipe',
      ]},
    )
