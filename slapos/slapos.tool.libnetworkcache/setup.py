from setuptools import setup, find_packages
import os

name = "slapos.tool.libnetworkcache"
version = 'O.1'


def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


long_description = (
        read('README.txt')
        + '\n' +
        read('CHANGES.txt')
    )

setup(
    name=name,
    version=version,
    description="libnetworkcache - Client for Networkcache HTTP Server",
    long_description=long_description,
    license="GPLv3",
    keywords="vifib slapos networkcache",
    classifiers=[
      ],
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    namespace_packages=['slapos', 'slapos.tool'],
    install_requires=[
    ],
    zip_safe=False,
    entry_points=""" """,
    )
