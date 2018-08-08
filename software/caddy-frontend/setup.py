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
