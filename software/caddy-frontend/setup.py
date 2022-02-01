# The caddyprofiledeps egg allows to set dependecies of the Caddy profiles
# which are enabled during the instance run, thanks to using caddyprofiledeps
# recipe

from setuptools import setup
setup(
  name='caddyprofiledeps',
  install_requires=[
    'validators',
    'furl',
    'orderedmultidict',
    'caucase',
    'python2-secrets',
  ],
  entry_points={
    'zc.buildout': [
      'default = caddyprofiledummy:Recipe',
    ],
    'console_scripts': [
      'smart-caucase-signer = caddyprofiledummy:smart_sign',
      'caucase-csr-sign-check = caddyprofiledummy:caucase_csr_sign_check'
    ]
  }
)
