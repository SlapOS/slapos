#  * sets additional dependencies for the instance processing
#  * provides instance's importable specific code

from setuptools import setup
setup(
  name='software',
  install_requires=[
    'validators',
    'furl',
    'dnspython',
  ],
  entry_points={
    'zc.buildout': [
      'default = software:Recipe',
    ]
  }
)
