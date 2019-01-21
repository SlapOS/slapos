##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
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

import os
import requests
import utils

# for development: debugging logs and install Ctrl+C handler
if os.environ.get('SLAPOS_TEST_DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


class HelloWorldTestCase(utils.SlapOSInstanceTestCase):
  # to be defined by subclasses
  name = None
  kind = None

  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')),)

  @classmethod
  def getInstanceParameterDict(cls):
    return {"name": cls.name}


class HTTPRequestTestMixin(object):
  """Test that the service url.${kind} responds Hello ${name}
  """
  def test_get(self):
    url = self.computer_partition.getConnectionParameterDict()['url.{}'.format(
        self.kind)]
    response = requests.get(url)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertTrue(
        response.text.startswith("Hello {}".format(self.name)), response.text)


class TestPython(HelloWorldTestCase, HTTPRequestTestMixin):
  name = "Python"
  kind = "python"


class TestRuby(HelloWorldTestCase, HTTPRequestTestMixin):
  name = "Ruby"
  kind = "ruby"


class TestGolang(HelloWorldTestCase, HTTPRequestTestMixin):
  name = "Go"
  kind = "go"
