##############################################################################
# coding: utf-8
#
# Copyright (c) 2020 Nexedi SA and Contributors. All Rights Reserved.
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
import json
import xmlrpclib
import ssl
import base64
import io

import PyPDF2


from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, CloudOOoTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


def getReferencedFonts(pdf_file_reader):
  """Return fonts referenced in this pdf
  """
  fonts = set()

  def collectFonts(obj):
    """Recursively visit PDF objects and collect referenced fonts in `fonts`
    """
    if hasattr(obj, 'keys'):
      if '/BaseFont' in obj:
        fonts.add(obj['/BaseFont'])
      for k in obj.keys():
        collectFonts(obj[k])

  for page in pdf_file_reader.pages:
    collectFonts(page.getObject()['/Resources'])
  return {font.split('+')[1] for font in fonts}


class TestCloudOOo(CloudOOoTestCase):
  def setUp(self):
    self.url = json.loads(
        self.computer_partition.getConnectionParameterDict()["_"])['cloudooo']

  def test_converted_pdf_fonts(self):
    # XXX ignore certificate
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    # TODO
    #self.url = 'https://cloudooo.erp5.net'
    #self.url = 'http://10.0.118.110:2020'
    server = xmlrpclib.ServerProxy(self.url, context=ssl_context)
    with open(os.path.join('data', 'test.odt')) as input_f:
      converted = server.convertFile(
          base64.encodestring(input_f.read()),
          'odt',
          'pdf',
      )
    pdf = PyPDF2.PdfFileReader(io.BytesIO(base64.decodestring(converted)))
    fonts = getReferencedFonts(pdf)
    self.assertEqual(
        {
            'Caladea-Regular',
            'Carlito',
            'DejaVuSans',
            'DejaVuSans-ExtraLight',
            'DejaVuSansCondensed',
            'DejaVuSansMono',
            'DejaVuSerif',
            'DejaVuSerifCondensed',
            'GentiumBasic',
            'GentiumBookBasic',
            'IPAexGothic',
            'IPAexMincho',
            'LiberationMono',
            'LiberationSans',
            'LiberationSansNarrow',
            'LiberationSerif',
            'LinuxLibertineG',
            'OpenSymbol',
            'Roboto-Black',
            'Roboto-Light',
            'Roboto-Medium',
            'Roboto-Regular',
            'Roboto-Thin',
            'RobotoCondensed-Light',
            'RobotoCondensed-Regular',
        },
        fonts,
    )
    # TODO this is still work in progress, I'm not sure which fonts are used...
    if 0:
      self.assertEqual(
          {
              'Caladea-Regular',
              'Carlito',
              'DejaVuMathTeXGyre-Regular',
              'DejaVuSans',
              'DejaVuSans-ExtraLight',
              'DejaVuSansCondensed',
              'DejaVuSansMono',
              'DejaVuSerif',
              'DejaVuSerifCondensed',
              'GentiumBasic',
              'GentiumBookBasic',
              'IPAexGothic',
              'IPAexMincho',
              'LiberationMono',
              'LiberationSans',
              'LiberationSansNarrow',
              'LiberationSerif',
              'OpenSymbol',
              'Roboto-Black',
              'Roboto-Light',
              'Roboto-Medium',
              'Roboto-Regular',
              'Roboto-Thin',
              'RobotoCondensed-Light',
              'RobotoCondensed-Regular',
          },
          fonts,
      )