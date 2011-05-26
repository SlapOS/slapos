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

extras_require = {
  'build': [],
  'buildcmmi': [],
}

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
        ],
      zip_safe=True,
      entry_points={
        'zc.buildout': [
          'build = slapos.recipe.build:Script',
          'buildcmmi = slapos.recipe.build:Cmmi',
      ]},
      extras_require=extras_require,
    )
