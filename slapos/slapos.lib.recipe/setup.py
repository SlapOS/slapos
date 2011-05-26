from setuptools import setup, find_packages

version = '1.0'
name = 'slapos.lib.recipe'
long_description = open("README.txt").read() + "\n" + \
    open("CHANGES.txt").read()

setup(name=name,
      version=version,
      description="Library, helpers and superclass for SlapOS zc.buildout recipes",
      long_description=long_description,
      classifiers=[
          "Framework :: Buildout",
          "Programming Language :: Python",
        ],
      keywords='slap librecipe',
      license='GPLv3',
      namespace_packages=['slapos'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      include_package_data=True,
      install_requires=[
        'netaddr', # to manipulate on IP addresses
        'setuptools', # namespaces
        'slapos.slap', # uses internally
        'zc.buildout', # plays with buildout
        'zc.recipe.egg', # for scripts generation
        ],
      zip_safe=True,
    )
