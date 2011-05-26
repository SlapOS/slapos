from setuptools import setup, find_packages

version = '1.0'
name = 'slapos.recipe.build'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read()

setup(name=name,
      version=version,
      description="Simple download recipe",
      long_description=long_description,
      classifiers=[
          "Framework :: Buildout :: Recipe",
          "Programming Language :: Python",
        ],
      keywords='slapos recipe build',
      license='GPLv3',
      namespace_packages=['slapos'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      include_package_data=True,
      install_requires=[
        'setuptools', # for namespace and internal usage
        'zc.buildout', # needed to play internally
        ],
      entry_points={'zc.buildout': [
        'default = %s:Script' % name,
        'cmmi = %s:Cmmi' % name,
        ]},
      zip_safe=True,
    )
