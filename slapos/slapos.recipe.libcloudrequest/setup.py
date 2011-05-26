from setuptools import setup, find_packages

version = '0.0.3'
name = 'slapos.recipe.libcloudrequest'
long_description = open("README.txt").read() + "\n" + open("CHANGES.txt").read()

setup(name=name,
      version=version,
      description="Slapified buildout recipe to request libcloud instance",
      long_description=long_description,
      classifiers=[
          "Framework :: Buildout :: Recipe",
          "Programming Language :: Python",
        ],
      keywords='slap recipe libcloud reques',
      license='GPLv3',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['slapos', 'slapos.recipe'],
      include_package_data=True,
      install_requires=[
        'setuptools',
        'slapos.lib.recipe',
        'zc.buildout',
        ],
      zip_safe=True,
      entry_points={'zc.buildout': ['default = %s:Recipe' % name]}
    )
