from setuptools import setup, find_packages

version = '1.0'
name = 'slapos.recipe.template'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read()

setup(name=name,
      version=version,
      description="collective.recipe.template with network input support",
      long_description=long_description,
      classifiers=[
          "Framework :: Buildout :: Recipe",
          "Programming Language :: Python",
        ],
      keywords='slapos download',
      license='GPLv3',
      namespace_packages=['slapos'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      include_package_data=True,
      install_requires=[
        'collective.recipe.template', # used for real run
        'setuptools', # for namespace
        'zc.buildout', # needed to play internally
        ],
      entry_points={'zc.buildout': ['default = %s:Recipe' % name]},
      zip_safe=True,
    )
