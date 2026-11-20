#  * sets additional dependencies for the instance processing
#  * provides instance's importable specific code

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
      'frontend-request = software:FrontendRequest',
      'frontend-slave-request = software:FrontendSlaveRequest',
    ],
    'console_scripts': [
      'smart-caucase-signer = software:smart_sign',
      'caucase-csr-sign-check = software:caucase_csr_sign_check',
      'haproxy-master-reload = software:haproxy_master_reload',
      'rapid-cdn-error-page-manager = software:error_page_manager_main',
      'rapid-cdn-error-page-updater = software:error_page_updater_main',
      'rapid-cdn-error-page-seed = software:error_page_seed_main'
    ]
  }
)
