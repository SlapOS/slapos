from setuptools import setup, find_packages

setup(
    name='slapos.test.warp10',
    version='0.0.1',
    description="Test for SlapOS' Warp 10",
    long_description="Tests for the Warp 10 platform software release",
    long_description_content_type='text/markdown',
    maintainer="SenX",
    maintainer_email="contact@senx.io",
    url="https://lab.nexedi.com/nexedi/slapos",
    packages=find_packages(),
    install_requires=[
        'slapos.core',
        'slapos.libnetworkcache',
        'erp5.util',
        'requests',
    ],
    zip_safe=True,
    test_suite='test',
)
