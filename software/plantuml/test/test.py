##############################################################################
# coding: utf-8
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
import requests
import plantuml

from slapos.recipe.librecipe import generateHashFromFiles
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import ImageComparisonTestCase


setUpModule, PlantUMLTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestSimpleDiagram(PlantUMLTestCase, ImageComparisonTestCase):
  def setUp(self):
    self.url = self.computer_partition.getConnectionParameterDict()["url"]
    self.plantuml = plantuml.PlantUML(
      url='{}/png/'.format(self.url),
      http_opts={"disable_ssl_certificate_validation": True}
    )

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
    # We just compare that image are similar.
    reference = Image.open(os.path.join(os.path.dirname(__file__), "data", "test_sequence_diagram.png"))
    self.assertImagesSame(Image.open(BytesIO(png)), reference)

  def test_sequence_diagram_skin_rose(self):
    # default theme changed, but we can use `skin rose` to keep old theme
    # https://github.com/plantuml/plantuml/issues/996
    png = self.plantuml.processes(textwrap.dedent("""\
    @startuml
    skin rose
    Bob -> Alice : hello
    Alice -> Bob : Go Away
    @enduml
    """))
    reference = Image.open(os.path.join(os.path.dirname(__file__), "data", "test_sequence_diagram_skin_rose.png"))
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

  def test_timing_diagram(self):
    png = self.plantuml.processes(textwrap.dedent("""\
    @startuml
    robust "Web Browser" as WB
    concise "Web User" as WU

    @0
    WU is Idle
    WB is Idle

    @100
    WU is Waiting
    WB is Processing

    @300
    WB is Waiting
    @enduml
    """))
    reference = Image.open(os.path.join(os.path.dirname(__file__), "data", "test_timing_diagram.png"))
    self.assertImagesSimilar(Image.open(BytesIO(png)), reference)

  def test_fonts(self):
    """Test slapos provided fonts are used"""
    png = self.plantuml.processes(textwrap.dedent("""\
    @startuml
    listfonts 私は申し訳ありません：私は日本語を話さない。Je ne parle pas japonais.
    @enduml
    """))
    # URL on the reference implementation would be
    # http://www.plantuml.com/plantuml/png/SoWkIImgAStDuSh9B2v9oyyhALPulhpnSUFwvrCsFswS_c85a6nwtDJrk77VuyRPZviclzyp2wBWsVIbp-QiUR5gtkEcIIzMRdpSEFLnuwh7ZIsF6vgyKXNoKXKA4ejoG6InGbPYGNvUOcQn7fT3QbuAq3O0
    # but we don't have same fonts, so we compare against the fonts of a slapos instance.
    reference = Image.open(os.path.join(os.path.dirname(__file__), "data", "test_fonts.png"))
    self.assertImagesSimilar(Image.open(BytesIO(png)), reference)

  def test_editor(self):
    """Test the embedded editor"""
    r = requests.get('{}/uml/'.format(self.url), verify=False)
    self.assertEqual(r.status_code, requests.codes.ok)

  def test_svg(self):
    """Test svg rendering"""
    image_key = plantuml.deflate_and_encode(textwrap.dedent("""\
    @startuml
    Bob -> Alice : hello
    Alice -> Bob : Go Away
    @enduml
    """))
    svg = requests.get('{}/svg/{}'.format(self.url, image_key), verify=False).text
    self.assertIn('<?xml version="1.0" encoding="UTF-8"', svg)

  def test_ascii_art(self):
    """Test ascii art rendering"""
    image_key = plantuml.deflate_and_encode(textwrap.dedent("""\
    @startuml
    Bob -> Alice : hello
    Alice -> Bob : Go Away
    @enduml
    """))
    aa = requests.get('{}/txt/{}'.format(self.url, image_key), verify=False).content
    with open(os.path.join(os.path.dirname(__file__), "data", "test_ascii_art.txt"), 'rb') as reference:
      self.assertEqual(aa, reference.read())


class ServicesTestCase(PlantUMLTestCase):

  def test_hashes(self):
    hash_files = [
      'var/tomcat/conf/server.xml',
      'software_release/buildout.cfg'
    ]
    expected_process_names = [
      'tomcat-instance-{hash}-on-watch',
    ]

    with self.slap.instance_supervisor_rpc as supervisor:
      process_names = [process['name']
                     for process in supervisor.getAllProcessInfo()]

    hash_files = [os.path.join(self.computer_partition_root_path, path)
                  for path in hash_files]

    for name in expected_process_names:
      h = generateHashFromFiles(hash_files)
      expected_process_name = name.format(hash=h)

      self.assertIn(expected_process_name, process_names)
