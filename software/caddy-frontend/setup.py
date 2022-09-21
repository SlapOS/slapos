# The software.py distribution allows to set additionaly dependencies for the
# profile instantiation and contains software specific scripts.
from setuptools import setup
setup(
  name='software',
  install_requires=[
    'validators',
    'furl',
    'orderedmultidict',
    'caucase',
    'python2-secrets',
  ],
  entry_points={
    'zc.buildout': [
      'default = software:Recipe',
    ],
    'console_scripts': [
      'smart-caucase-signer = software:smart_sign',
      'caucase-csr-sign-check = software:caucase_csr_sign_check'
    ]
  }
)
