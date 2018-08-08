# The caddyprofiledeps egg allows to set dependecies of the Caddy profiles
# which are enabled during the instance run, thanks to using caddyprofiledeps
# recipe

from setuptools import setup
setup(
  name='caddyprofiledeps',
  install_requires=[
    'validators',
  ],
  entry_points={
    'zc.buildout': [
      'default = caddyprofiledummy:Recipe',
    ]
  }
)
