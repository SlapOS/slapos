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
import six.moves.xmlrpc_client as xmlrpclib
import ssl
import base64
import io

import PyPDF2

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, CloudOooTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

# Cloudooo needs a lot of time before being available.
CloudOooTestCase.instance_max_retry = 30


def normalizeFontName(font_name):
  if '+' in font_name:
    return font_name.split('+')[1]
  if font_name.startswith('/'):
    return font_name[1:]


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

  return {normalizeFontName(font) for font in fonts}


class HTMLtoPDFConversionFontTestMixin:
  """Mix-In class to test how fonts are selected during
  HTML to PDF conversions.

  This needs to be mixed with a test case defining:

  * pdf_producer : the name of /Producer in PDF metadata
  * expected_font_mapping : a mapping of resulting font name in pdf,
    keyed by font-family in the input html
  * _convert_html_to_pdf: a method to to convert html to pdf
  """
  def _convert_html_to_pdf(self, src_html):
    # type: (str) -> bytes
    """Convert the HTML source to pdf bytes.
    """

  def setUp(self):
    self.url = json.loads(
        self.computer_partition.getConnectionParameterDict()["_"])['cloudooo']
    # XXX ignore certificate errors
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    self.server = xmlrpclib.ServerProxy(
        self.url,
        context=ssl_context,
        allow_none=True,
    )

  def test(self):
    actual_font_mapping_mapping = {}
    for font, expected_substitution in sorted(
        self.expected_font_mapping.items()):
      src_html = '''
      <style>
          p {{ font-family: "{font}"; font-size: 20pt; }}
      </style>
      <p>the quick brown fox jumps over the lazy dog.</p>
      <p>THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG.</p>
      '''.format(**locals())

      pdf_data = self._convert_html_to_pdf(src_html)
      pdf_reader = PyPDF2.PdfFileReader(io.BytesIO((pdf_data)))
      self.assertEqual(
          self.pdf_producer,
          pdf_reader.getDocumentInfo()['/Producer'])
      fonts_in_pdf = getReferencedFonts(pdf_reader)

      if len(fonts_in_pdf) == 1:
        actual_font_mapping_mapping[font] = fonts_in_pdf.pop()
      else:
        actual_font_mapping_mapping[font] = fonts_in_pdf

      if self.debug:
        test_id = self.id()  # pylint:disable=unused-variable
        with open('data/reference-{test_id}-{font}.pdf'.format(**locals()),
                  'wb') as f:
          f.write(pdf_data)
        self.logger.debug(
            "%s: expect:%s got:%s", font, expected_substitution,
            actual_font_mapping_mapping[font])

    self.maxDiff = None
    self.assertEqual(self.expected_font_mapping, actual_font_mapping_mapping)


class TestWkhtmlToPDF(HTMLtoPDFConversionFontTestMixin, CloudOooTestCase):
  __partition_reference__ = 'wk'
  pdf_producer = 'Qt 4.8.7'
  expected_font_mapping = {
      'Arial Black': 'Roboto-Medium',
      'Arial': 'Roboto-Medium',
      'Avant Garde': 'Roboto-Medium',
      'Bookman': 'Roboto-Medium',
      'Carlito': 'Roboto-Medium',
      'Comic Sans MS': 'Roboto-Medium',
      'Courier New': 'Roboto-Medium',
      'DejaVu Sans Condensed': 'Roboto-Medium',
      'DejaVu Sans ExtraLight': 'Roboto-Medium',
      'DejaVu Sans Mono': 'Roboto-Medium',
      'DejaVu Sans': 'Roboto-Medium',
      'DejaVu Serif Condensed': 'Roboto-Medium',
      'DejaVu Serif': 'Roboto-Medium',
      'Garamond': 'Roboto-Medium',
      'Gentium Basic': 'Roboto-Medium',
      'Gentium Book Basic': 'Roboto-Medium',
      'Georgia': 'Roboto-Medium',
      'Helvetica': 'Roboto-Medium',
      'Impact': 'Roboto-Medium',
      'IPAex Gothic': 'Roboto-Medium',
      'IPAex Mincho': 'Roboto-Medium',
      'Liberation Mono': 'LiberationMono',
      'Liberation Sans Narrow': 'Roboto-Medium',
      'Liberation Sans': 'LiberationSans',
      'Liberation Serif': 'LiberationSerif',
      'Linux LibertineG': 'Roboto-Medium',
      'OpenSymbol': 'Roboto-Medium',
      'Palatino': 'Roboto-Medium',
      'Roboto Black': 'Roboto-Medium',
      'Roboto Condensed Light': 'Roboto-Medium',
      'Roboto Condensed Regular': 'Roboto-Medium',
      'Roboto Light': 'Roboto-Medium',
      'Roboto Medium': 'Roboto-Medium',
      'Roboto Thin': 'Roboto-Medium',
      'Times New Roman': 'Roboto-Medium',
      'Trebuchet MS': 'Roboto-Medium',
      'Verdana': 'Roboto-Medium',
      'ZZZdefault fonts when no match': 'Roboto-Medium',
  }

  def _convert_html_to_pdf(self, src_html):
    return base64.decodestring(
        self.server.convertFile(
            base64.encodestring(src_html.encode()).decode(),
            'html',
            'pdf',
            False,
            False,
            {
                'encoding': 'utf-8'
            },
        ).encode())


class TestLibreoffice(HTMLtoPDFConversionFontTestMixin, CloudOooTestCase):
  __partition_reference__ = 'lo'
  pdf_producer = 'LibreOffice 5.2'
  expected_font_mapping = {
      'Arial Black': 'LinuxLibertineG',
      'Arial': 'LinuxLibertineG',
      'Avant Garde': 'LinuxLibertineG',
      'Bookman': 'LinuxLibertineG',
      'Carlito': 'Carlito',
      'Comic Sans MS': 'LinuxLibertineG',
      'Courier New': 'LinuxLibertineG',
      'DejaVu Sans Condensed': 'DejaVuSansCondensed',
      'DejaVu Sans ExtraLight': 'LinuxLibertineG',
      'DejaVu Sans Mono': 'DejaVuSansMono',
      'DejaVu Sans': 'DejaVuSans',
      'DejaVu Serif Condensed': 'DejaVuSerifCondensed',
      'DejaVu Serif': 'DejaVuSerif',
      'Garamond': 'LinuxLibertineG',
      'Gentium Basic': 'GentiumBasic',
      'Gentium Book Basic': 'GentiumBookBasic',
      'Georgia': 'LinuxLibertineG',
      'Helvetica': 'LinuxLibertineG',
      'Impact': 'LinuxLibertineG',
      'IPAex Gothic': 'IPAexGothic',
      'IPAex Mincho': 'IPAexMincho',
      'Liberation Mono': 'LiberationMono',
      'Liberation Sans Narrow': 'LiberationSansNarrow',
      'Liberation Sans': 'LiberationSans',
      'Liberation Serif': 'LiberationSerif',
      'Linux LibertineG': 'LinuxLibertineG',
      'OpenSymbol': 'OpenSymbol',
      'Palatino': 'LinuxLibertineG',
      'Roboto Black': 'Roboto-Black',
      'Roboto Condensed Light': 'RobotoCondensed-Light',
      'Roboto Condensed Regular': 'LinuxLibertineG',
      'Roboto Light': 'Roboto-Light',
      'Roboto Medium': 'Roboto-Medium',
      'Roboto Thin': 'Roboto-Thin',
      'Times New Roman': 'LinuxLibertineG',
      'Trebuchet MS': 'LinuxLibertineG',
      'Verdana': 'LinuxLibertineG',
      'ZZZdefault fonts when no match': 'LinuxLibertineG',
  }

  def _convert_html_to_pdf(self, src_html):
    return base64.decodestring(
        self.server.convertFile(
            base64.encodestring(src_html.encode()).decode(),
            'html',
            'pdf',
        ).encode())
