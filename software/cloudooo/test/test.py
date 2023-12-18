##############################################################################
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

import codecs
import csv
import multiprocessing
import os
import json
import xmlrpc.client as xmlrpclib
import urllib.parse as urllib_parse
import ssl
import base64
import io

import requests
import PIL.Image
import PyPDF2

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import ImageComparisonTestCase


setUpModule, _CloudOooTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class CloudOooTestCase(_CloudOooTestCase):
  # Cloudooo needs a lot of time before being available.
  instance_max_retry = 30

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
    self.addCleanup(self.server('close'))


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

  def test(self):
    actual_font_mapping_mapping = {}
    for font in self.expected_font_mapping:
      src_html = f'''
      <style>
          p {{ font-family: "{font}"; font-size: 20pt; }}
      </style>
      <p>the quick brown fox jumps over the lazy dog.</p>
      <p>THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG.</p>
      '''

      pdf_data = self._convert_html_to_pdf(src_html)
      pdf_reader = PyPDF2.PdfFileReader(io.BytesIO(pdf_data))
      self.assertEqual(
          self.pdf_producer,
          pdf_reader.getDocumentInfo()['/Producer'])
      fonts_in_pdf = getReferencedFonts(pdf_reader)

      if len(fonts_in_pdf) == 1:
        actual_font_mapping_mapping[font] = fonts_in_pdf.pop()
      else:
        actual_font_mapping_mapping[font] = fonts_in_pdf

    self.maxDiff = None
    self.assertEqual(self.expected_font_mapping, actual_font_mapping_mapping)


class TestWkhtmlToPDF(HTMLtoPDFConversionFontTestMixin, CloudOooTestCase):
  __partition_reference__ = 'wk'
  pdf_producer = 'Qt 4.8.7'
  expected_font_mapping = {
      'Arial': 'LiberationSans',
      'Arial Black': 'LiberationSans',
      'Avant Garde': 'LiberationSans',
      'Bookman': 'LiberationSans',
      'Carlito': 'Carlito',
      'Comic Sans MS': 'LiberationSans',
      'Courier New': 'LiberationSans',
      'DejaVu Sans': 'DejaVuSans',
      'DejaVu Sans Condensed': 'LiberationSans',
      'DejaVu Sans Mono': 'DejaVuSansMono',
      'DejaVu Serif': 'DejaVuSerif',
      'DejaVu Serif Condensed': 'LiberationSans',
      'Garamond': 'LiberationSans',
      'Gentium Basic': 'GentiumBasic',
      'Gentium Book Basic': 'GentiumBookBasic',
      'Georgia': 'LiberationSans',
      'Helvetica': 'LiberationSans',
      'IPAex Gothic': 'LiberationSans',
      'IPAex Mincho': 'LiberationSans',
      'Impact': 'LiberationSans',
      'Liberation Mono': 'LiberationMono',
      'Liberation Sans': 'LiberationSans',
      'Liberation Sans Narrow': 'LiberationSansNarrow',
      'Liberation Serif': 'LiberationSerif',
      'Linux LibertineG': 'LiberationSans',
      'OpenSymbol': {'DejaVuSans', 'OpenSymbol'},
      'Palatino': 'LiberationSans',
      'Roboto Black': 'LiberationSans',
      'Roboto Condensed Light': 'LiberationSans',
      'Roboto Condensed': 'RobotoCondensed-Regular',
      'Roboto Light': 'LiberationSans',
      'Roboto Medium': 'LiberationSans',
      'Roboto Thin': 'LiberationSans',
      'Times New Roman': 'LiberationSans',
      'Trebuchet MS': 'LiberationSans',
      'Verdana': 'LiberationSans',
      'ZZZdefault fonts when no match': 'LiberationSans'
  }

  def _convert_html_to_pdf(self, src_html):
    return base64.decodebytes(
        self.server.convertFile(
            base64.encodebytes(src_html.encode()).decode(),
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
  pdf_producer = 'LibreOffice 7.5'
  expected_font_mapping = {
      'Arial': 'LiberationSans',
      'Arial Black': 'DejaVuSans',
      'Avant Garde': 'DejaVuSans',
      'Bookman': 'DejaVuSans',
      'Carlito': 'Carlito',
      'Comic Sans MS': 'DejaVuSans',
      'Courier New': 'LiberationMono',
      'DejaVu Sans': 'DejaVuSans',
      'DejaVu Sans Condensed': 'DejaVuSansCondensed',
      'DejaVu Sans Mono': 'DejaVuSansMono',
      'DejaVu Serif': 'DejaVuSerif',
      'DejaVu Serif Condensed': 'DejaVuSerifCondensed',
      'Garamond': 'DejaVuSerif',
      'Gentium Basic': 'GentiumBasic',
      'Gentium Book Basic': 'GentiumBookBasic',
      'Georgia': 'DejaVuSerif',
      'Helvetica': 'LiberationSans',
      'IPAex Gothic': 'IPAexGothic',
      'IPAex Mincho': 'IPAexMincho',
      'Impact': 'DejaVuSans',
      'Liberation Mono': 'LiberationMono',
      'Liberation Sans': 'LiberationSans',
      'Liberation Sans Narrow': 'LiberationSansNarrow',
      'Liberation Serif': 'LiberationSerif',
      'Linux LibertineG': 'LinuxLibertineG',
      'OpenSymbol': {'OpenSymbol', 'IPAMincho'},
      'Palatino': 'DejaVuSerif',
      'Roboto Black': 'Roboto-Black',
      'Roboto Condensed Light': 'RobotoCondensed-Light',
      'Roboto Condensed': 'RobotoCondensed-Regular',
      'Roboto Light': 'Roboto-Light',
      'Roboto Medium': 'Roboto-Medium',
      'Roboto Thin': 'Roboto-Thin',
      'Times New Roman': 'LiberationSerif',
      'Trebuchet MS': 'DejaVuSans',
      'Verdana': 'DejaVuSans',
      'ZZZdefault fonts when no match': 'DejaVuSans'
  }

  def _convert_html_to_pdf(self, src_html):
    return base64.decodebytes(
        self.server.convertFile(
            base64.encodebytes(src_html.encode()).decode(),
            'html',
            'pdf',
        ).encode())


class TestLibreofficeDrawToPNGConversion(CloudOooTestCase, ImageComparisonTestCase):
  __partition_reference__ = 'l'

  def test(self):
    reference_png = PIL.Image.open(os.path.join('data', f'{self.id()}.png'))
    with open(os.path.join('data', f'{self.id()}.odg'), 'rb') as f:
      actual_png_data = base64.decodebytes(
        self.server.convertFile(
          base64.encodebytes(f.read()).decode(),
          'odg',
          'png',
        ).encode())
      actual_png = PIL.Image.open(io.BytesIO(actual_png_data))

    # save a snapshot
    with open(os.path.join(self.computer_partition_root_path, self.id() + '.png'), 'wb') as f:
      f.write(actual_png_data)

    self.assertImagesSame(actual_png, reference_png)


class TestLibreOfficeTextConversion(CloudOooTestCase):
  __partition_reference__ = 'txt'

  def test_html_to_text(self):
    self.assertEqual(
        base64.decodebytes(
            self.server.convertFile(
                base64.encodebytes(
                    '<html>héhé</html>'.encode()).decode(),
                'html',
                'txt',
            ).encode()),
        codecs.BOM_UTF8 + b'h\xc3\xa9h\xc3\xa9\n',
    )


class TestLibreOfficeCluster(CloudOooTestCase):
  __partition_reference__ = 'lc'

  @classmethod
  def getInstanceParameterDict(cls):
    return {'backend-count': 4}

  def test_multiple_conversions(self):
    # make this function global so that it can be picked and used by multiprocessing
    global _convert_html_to_text

    def _convert_html_to_text(src_html):
      return base64.decodebytes(
          self.server.convertFile(
              base64.encodebytes(src_html.encode()).decode(),
              'html',
              'txt',
          ).encode())

    pool = multiprocessing.Pool(5)
    with pool:
      converted = pool.map(
        _convert_html_to_text,
        ['<html><body>hello</body></html>'] * 100)

    self.assertEqual(converted, [codecs.BOM_UTF8 + b'hello\n'] * 100)

    # haproxy stats are exposed
    res = requests.get(
        urllib_parse.urljoin(self.url, '/haproxy;csv'),
        verify=False,
    )
    reader = csv.DictReader(io.StringIO(res.text))
    line_list = list(reader)
    # requests have been balanced
    total_hrsp_2xx = {
        line['svname']: int(line['hrsp_2xx'])
        for line in line_list
    }
    self.assertEqual(total_hrsp_2xx['FRONTEND'], 100)
    self.assertEqual(total_hrsp_2xx['BACKEND'], 100)
    for backend in 'cloudooo_1', 'cloudooo_2', 'cloudooo_3', 'cloudooo_4':
      # ideally there should be 25% of requests on each backend, because we use
      # round robin scheduling, but it can happen that some backend take longer
      # to start, so we are tolerant here and just check that each backend
      # process at least one request.
      self.assertGreater(total_hrsp_2xx[backend], 0)
    # no errors
    total_eresp = {
        line['svname']: int(line['eresp'] or 0)
        for line in line_list
    }
    self.assertEqual(
        total_eresp, {
            'FRONTEND': 0,
            'cloudooo_1': 0,
            'cloudooo_2': 0,
            'cloudooo_3': 0,
            'cloudooo_4': 0,
            'BACKEND': 0,
        })
