##############################################################################
#
# Copyright (c) 2018 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from setuptools import setup, find_packages
import glob
import os

version = '0.0.1.dev0'
name = 'slapos.test.proftpd'
long_description = open("README.md").read()

setup(name=name,
      version=version,
      description="Test for SlapOS' ProFTPd",
      long_description=long_description,
      long_description_content_type='text/markdown',
      maintainer="Nexedi",
      maintainer_email="info@nexedi.com",
      url="https://lab.nexedi.com/nexedi/slapos",
      packages=find_packages(),
      install_requires=[
        'slapos.core',
        'erp5.util',
        'pysftp',
        'supervisor',
        ],
      zip_safe=True,
      test_suite='test',
    )
