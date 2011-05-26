from setuptools import setup, find_packages

version = '0.1'
name = 'slapos.recipebox'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read()

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
    )
