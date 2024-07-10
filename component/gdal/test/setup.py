"""
Configuration for GDAL test.

pyproject.toml cannot be used, as the version 3.2.3 of GDAL (the newest version
which still supports Python 2) require setuptools<58.0.0
(https://github.com/pypa/setuptools/issues/2781), while setuptools>=61.0 is
required to be able to store the metadata in pyproject.toml, as per PEP621.
"""
# PY3: Upgrade GDAL and switch to pyproject.toml
from setuptools import setup, find_packages

version = "0.0.1.dev0"
name = "slapos.test.gdal"
with open("README.md") as f:
    long_description = f.read()

setup(
    name=name,
    version=version,
    description="Test for SlapOS' GDAL component",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GNU General Public License version 3 or later",
    maintainer="Nexedi",
    maintainer_email="info@nexedi.com",
    url="https://lab.nexedi.com/nexedi/slapos",
    packages=find_packages(),
    install_requires=[
        "slapos.core",
        "slapos.libnetworkcache",
        "erp5.util",
    ],
    zip_safe=True,
    test_suite="test",
    keywords=[
        "SlapOS",
        "testing",
        "GDAL",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Testing",
        "Typing :: Typed",
    ],
)

