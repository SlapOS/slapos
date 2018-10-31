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

import os
import textwrap
import hashlib
from io import BytesIO

from PIL import Image
import plantuml

import utils

# for development: debugging logs and install Ctrl+C handler
if os.environ.get('DEBUG'):
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import unittest
  unittest.installHandler()


class PlantUMLTestCase(utils.SlapOSInstanceTestCase):
  @classmethod
  def getSoftwareURLList(cls):
    return (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'software.cfg')), )


class TestSimpleDiagram(PlantUMLTestCase):
  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict()["url"]
    self.plantuml = plantuml.PlantUML(
      url=self.url,
      http_opts={"disable_ssl_certificate_validation": True}
    )

  def assertImagesSimilar(self, i1, i2):
    """Assert images are 5% similar
   taken from https://rosettacode.org/wiki/Percentage_difference_between_images
    """
    pairs = zip(i1.getdata(), i2.getdata())
    if len(i1.getbands()) == 1:
      # for gray-scale jpegs
      dif = sum(abs(p1-p2) for p1,p2 in pairs)
    else:
      dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))

    ncomponents = i1.size[0] * i1.size[1] * 3
    self.assertLess((dif / 255.0 * 100) / ncomponents, 5)

  def assertImagesSame(self, i1, i2):
    """Assert images are exactly same."""
    self.assertEqual(list(i1.getdata()), list(i2.getdata()))

  def test_sequence_diagram(self):
    png = self.plantuml.processes(textwrap.dedent("""\
    @startuml
    Bob -> Alice : hello
    Alice -> Bob : Go Away
    @enduml
    """))
    # we cannot just compare the hash of the image against a reference that can be found with
    # http://www.plantuml.com/plantuml/png/SoWkIImgAStDuNBAJrBGjLDmpCbCJbMmKiX8pSd9vuBmWC8WMIi5ztm5n_B4IYw7rBmKe1u0
    # because plantuml include information about the server in the output image metadata ( you can
    # use http://exif.regex.info/exif.cgi to see metadata )
    # So we process the image to remove metadata.
    reference = Image.open(os.path.join(os.path.dirname(__file__), "data", "test_sequence_diagram.png"))
    self.assertImagesSame(Image.open(BytesIO(png)), reference)

  def test_class_diagram(self):
    """Class diagram require a working graphviz installation"""
    png = self.plantuml.processes(textwrap.dedent("""\
    @startuml
    class Car

    Driver - Car : drives >
    Car *- Wheel : have 4 >
    Car -- Person : < owns

    @enduml
    """))
    # rendering is not exactly same on class diagrams, because of fonts and maybe also something in graphviz.
    # We just compare that image are similar.

    # http://www.plantuml.com/plantuml/png/SoWkIImgAStDuKhEIImkLd1EBEBYSYdAB4ijKj05yHIi5590t685EouGLqjN8JmZDJK7A9wHM9QgO08LrzLL24WjAixF0qhOAEINvnLpSJcavgK0ZGO0
    reference = Image.open(os.path.join(os.path.dirname(__file__), "data", "test_class_diagram.png"))
    self.assertImagesSimilar(Image.open(BytesIO(png)), reference)


class ServicesTestCase(PlantUMLTestCase):
  @staticmethod
  def generateHashFromFiles(file_list):
    hasher = hashlib.md5()
    for path in file_list:
      with open(path, 'r') as afile:
        buf = afile.read()
      hasher.update("%s\n" % len(buf))
      hasher.update(buf)
    hash = hasher.hexdigest()
    return hash

  def test_hashes(self):
    hash_files = [
      'software_release/buildout.cfg',
      'var/tomcat/conf/server.xml'
    ]
    expected_process_names = [
      'tomcat-instance-{hash}-on-watch',
    ]

    supervisor = self.getSupervisorRPCServer().supervisor
    process_names = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = ServicesTestCase.generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)