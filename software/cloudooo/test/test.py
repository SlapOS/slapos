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

# pyright: strict

from __future__ import annotations

import base64
import codecs
import csv
import io
import itertools
import json
import multiprocessing
import ssl
import textwrap
import urllib.parse as urllib_parse
import xmlrpc.client as xmlrpclib
from functools import partial
from pathlib import Path
from typing import AbstractSet, Callable, Dict, Mapping

import PIL.Image
import pypdf
import requests
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass
from slapos.testing.utils import ImageComparisonTestCase

setUpModule, _CloudOooTestCase = makeModuleSetUpAndTestCaseClass(
  Path(__file__).parent.parent / "software.cfg",
)


def open_cloudooo_connection(url: str) -> xmlrpclib.ServerProxy:
  """
  Open a RPC connection with Cloudooo.

  Args:
    url: The URL of the CloudOoo server.

  Returns:
    A object that manages communication with CloudOoo via XML-RCP.

  """
  # XXX ignore certificate errors
  ssl_context = ssl.create_default_context()
  ssl_context.check_hostname = False
  ssl_context.verify_mode = ssl.CERT_NONE
  return xmlrpclib.ServerProxy(
    url,
    context=ssl_context,
    allow_none=True,
  )


def convert_file(
  file: bytes,
  source_format: str,
  destination_format: str,
  *,
  zip: bool = False,
  refresh: bool = False,
  conversion_kw: Dict[str, object] = {},
  server: xmlrpclib.ServerProxy,
) -> bytes:
  """
  Converts a file using CloudOoo.

  This is a helper function that does the necessary encoding/decoding,
  providing type-safety and keyword arguments.

  Args:
    file: The file contents to send to CloudOoo.
    source_format: Format of the input file.
    destination_format: Format of the output file.
    zip: Whether a zip file should be returned.
    refresh: Whether dynamic properties of document should be replaced
      before conversion.
    conversion_kw: Additional arguments for the conversion.
    server: The server used to send requests to Cloudooo.

  Returns:
    Contents of the converted file.

  """
  converted_file = server.convertFile(
    base64.encodebytes(file).decode(),
    source_format,
    destination_format,
    zip,
    refresh,
    conversion_kw,
  )

  assert isinstance(converted_file, str)

  return base64.decodebytes(converted_file.encode())


class CloudOooTestCase(_CloudOooTestCase):
  """
  Parent class for all CloudOoo tests.

  This class sets some attributes in the `setUp` method that are necessary
  for testing CloudOoo.

  Attributes:
    url: The URL of the CloudOoo server.
    server: A object that manages communication with CloudOoo via XML-RCP.

  """

  # Cloudooo needs a lot of time before being available.
  instance_max_retry = 30

  def setUp(self):
    self.url: str = json.loads(
      self.computer_partition.getConnectionParameterDict()["_"]
    )["cloudooo"]
    self.server = open_cloudooo_connection(self.url)
    self.addCleanup(self.server("close"))

  def convert_file(
    self,
    file: bytes,
    source_format: str,
    destination_format: str,
    *,
    zip: bool = False,
    refresh: bool = False,
    conversion_kw: Dict[str, object] = {},
  ) -> bytes:
    """
    Converts a file using CloudOoo.

    This is a helper method that does the necessary encoding/decoding,
    providing type-safety and keyword arguments.

    Args:
      file: The file contents to send to CloudOoo.
      source_format: Format of the input file.
      destination_format: Format of the output file.
      zip: Whether a zip file should be returned.
      refresh: Whether dynamic properties of document should be replaced
        before conversion.
      conversion_kw: Additional arguments for the conversion.

    Returns:
      Contents of the converted file.

    """
    return convert_file(
      file=file,
      source_format=source_format,
      destination_format=destination_format,
      zip=zip,
      refresh=refresh,
      conversion_kw=conversion_kw,
      server=self.server,
    )

  def script_test_basic(self) -> bytes:
    """
    Tries to execute a hello world script.

    Returns:
      The file contents in base64. If the script is executed
      properly, it should contain the string ``"Hello World"``,
      preceded by the UTF-8 BOM and with a trailing newline.
    """
    script = textwrap.dedent(
      """\
          # Get the XText interface
          text = Document.Text

          # Create an XTextRange at the end of the document
          tRange = text.End

          # Set the string
          tRange.String = "Hello World"
          """,
    )

    return self.convert_file(
      b"<html></html>",
      "html",
      "txt",
      conversion_kw={"script": script},
    )


QT_FONT_MAPPING: Mapping[str, str | AbstractSet[str]] = {
  "Arial": "LiberationSans",
  "Arial Black": "LiberationSans",
  "Avant Garde": "LiberationSans",
  "Bookman": "LiberationSans",
  "Carlito": "Carlito",
  "Comic Sans MS": "LiberationSans",
  "Courier New": "LiberationSans",
  "DejaVu Sans": "DejaVuSans",
  "DejaVu Sans Condensed": "LiberationSans",
  "DejaVu Sans Mono": "DejaVuSansMono",
  "DejaVu Serif": "DejaVuSerif",
  "DejaVu Serif Condensed": "LiberationSans",
  "Garamond": "LiberationSans",
  "Gentium Basic": "GentiumBasic",
  "Gentium Book Basic": "GentiumBookBasic",
  "Georgia": "LiberationSans",
  "Helvetica": "LiberationSans",
  "IPAex Gothic": "LiberationSans",
  "IPAex Mincho": "LiberationSans",
  "Impact": "LiberationSans",
  "Liberation Mono": "LiberationMono",
  "Liberation Sans": "LiberationSans",
  "Liberation Sans Narrow": "LiberationSansNarrow",
  "Liberation Serif": "LiberationSerif",
  "Linux LibertineG": "LiberationSans",
  "OpenSymbol": {"NotoSans-Regular", "OpenSymbol"},
  "Palatino": "LiberationSans",
  "Roboto Black": "LiberationSans",
  "Roboto Condensed Light": "LiberationSans",
  "Roboto Condensed": "RobotoCondensed-Regular",
  "Roboto Light": "LiberationSans",
  "Roboto Medium": "LiberationSans",
  "Roboto Thin": "LiberationSans",
  "Times New Roman": "LiberationSans",
  "Trebuchet MS": "LiberationSans",
  "Verdana": "LiberationSans",
  "ZZZdefault fonts when no match": "LiberationSans",
}

LIBREOFFICE_FONT_MAPPING: Mapping[str, str | AbstractSet[str]] = {
  "Arial": "LiberationSans",
  "Arial Black": "NotoSans-Regular",
  "Avant Garde": "NotoSans-Regular",
  "Bookman": "NotoSans-Regular",
  "Carlito": "Carlito",
  "Comic Sans MS": "NotoSans-Regular",
  "Courier New": "LiberationMono",
  "DejaVu Sans": "DejaVuSans",
  "DejaVu Sans Condensed": "DejaVuSansCondensed",
  "DejaVu Sans Mono": "DejaVuSansMono",
  "DejaVu Serif": "DejaVuSerif",
  "DejaVu Serif Condensed": "DejaVuSerifCondensed",
  "Garamond": "NotoSerif-Regular",
  "Gentium Basic": "GentiumBasic",
  "Gentium Book Basic": "GentiumBookBasic",
  "Georgia": "NotoSerif-Regular",
  "Helvetica": "LiberationSans",
  "IPAex Gothic": "IPAexGothic",
  "IPAex Mincho": "IPAexMincho",
  "Impact": "NotoSans-Regular",
  "Liberation Mono": "LiberationMono",
  "Liberation Sans": "LiberationSans",
  "Liberation Sans Narrow": "LiberationSansNarrow",
  "Liberation Serif": "LiberationSerif",
  "Linux LibertineG": "LinuxLibertineG",
  "OpenSymbol": {"OpenSymbol", "IPAMincho"},
  "Palatino": "NotoSerif-Regular",
  "Roboto Black": "Roboto-Black",
  "Roboto Condensed Light": "RobotoCondensed-Light",
  "Roboto Condensed": "RobotoCondensed-Regular",
  "Roboto Light": "Roboto-Light",
  "Roboto Medium": "Roboto-Medium",
  "Roboto Thin": "Roboto-Thin",
  "Times New Roman": "LiberationSerif",
  "Trebuchet MS": "NotoSans-Regular",
  "Verdana": "NotoSans-Regular",
  "ZZZdefault fonts when no match": "NotoSans-Regular",
}


def normalize_font_name(font_name: str) -> str:
  """
  Normalize a font name.

  As with other PostScript markup, font names are written with a leading
  slash symbol ("/"), which has to be stripped to obtain the conventional font
  name.

  Moreover, the standard allows also to define "font subsets", for which a tag
  followed by a plus sign ("+") precedes the actual font name:
  https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf#page=266
  This tag is also removed by this function.

  Args:
    font_name: The font name to normalize.

  Returns:
    Normalized font name.

  """
  if "+" in font_name:
    return font_name.split("+")[1]

  if font_name.startswith("/"):
    return font_name[1:]

  raise ValueError("Invalid font name")


def get_referenced_fonts(
  pdf_file_reader: pypdf.PdfReader,
) -> AbstractSet[str]:
  """
  Return fonts referenced in a pdf.

  Returns a set with all font names (normalized) present in a PDF.

  Args:
    pdf_file_reader: PDF reader.

  Returns:
    Set of font names present in the PDF.

  """
  return {
    normalize_font_name(font)
    for page in pdf_file_reader.pages
    for font in itertools.chain(
      *page._get_fonts()  # pyright: ignore[reportPrivateUsage]
    )
  }


class TestDefaultInstance(CloudOooTestCase, ImageComparisonTestCase):
  """Tests for CloudOoo instance with default configuration."""

  __partition_reference__ = "co_default"

  def assert_pdf_conversion_metadata(
    self,
    convert_html_to_pdf: Callable[[bytes], bytes],
    *,
    expected_producer: str,
    expected_font_mapping: Mapping[str, str | AbstractSet[str]],
  ) -> None:
    actual_font_mapping_mapping = {}

    for font in expected_font_mapping:
      src_html = f"""
            <style>
                p {{ font-family: "{font}"; font-size: 20pt; }}
            </style>
            <p>the quick brown fox jumps over the lazy dog.</p>
            <p>THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG.</p>
            """

      pdf_data = convert_html_to_pdf(src_html.encode())
      pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_data))

      metadata = pdf_reader.metadata
      assert metadata

      self.assertEqual(
        metadata.producer,
        expected_producer,
      )

      fonts_in_pdf = get_referenced_fonts(pdf_reader)

      font_or_set: str | AbstractSet[str] = fonts_in_pdf
      if len(fonts_in_pdf) == 1:
        # Tuple unpacking
        (font_or_set,) = fonts_in_pdf

      actual_font_mapping_mapping[font] = font_or_set

    self.assertEqual(actual_font_mapping_mapping, expected_font_mapping)

  def html_to_pdf_wkhtmltopdf_convert(self, src_html: bytes) -> bytes:
    """HTML to PDF conversion using wkhtmltopdf."""
    return self.convert_file(
      src_html,
      "html",
      "pdf",
      conversion_kw={"encoding": "utf-8"},
    )

  def test_html_to_pdf_wkhtmltopdf(self):
    """Test HTML to PDF conversion using wkhtmltopdf."""
    self.assert_pdf_conversion_metadata(
      self.html_to_pdf_wkhtmltopdf_convert,
      expected_producer="Qt 4.8.7",
      expected_font_mapping=QT_FONT_MAPPING,
    )

  def html_to_pdf_libreoffice_convert(self, src_html: bytes) -> bytes:
    """HTML to PDF conversion using LibreOffice."""
    return self.convert_file(
      src_html,
      "html",
      "pdf",
    )

  def test_html_to_pdf_libreoffice_convert(self):
    """Test HTML to PDF conversion using wkhtmltopdf."""
    self.assert_pdf_conversion_metadata(
      self.html_to_pdf_libreoffice_convert,
      expected_producer="LibreOffice 7.5",
      expected_font_mapping=LIBREOFFICE_FONT_MAPPING,
    )

  def test_draw_to_png(self):
    """Test Draw's ODG to PNG conversion."""
    reference_png = PIL.Image.open("data/test_draw_to_png.png")
    with open("data/test_draw_to_png.odg", "rb") as f:
      actual_png_data = self.convert_file(
        f.read(),
        "odg",
        "png",
      )
      actual_png = PIL.Image.open(io.BytesIO(actual_png_data))

    # Save a snapshot
    with open(
      Path(self.computer_partition_root_path) / "test_draw_to_png.png",
      "wb",
    ) as f:
      f.write(actual_png_data)

    self.assertImagesSame(actual_png, reference_png)

  def test_html_to_text(self):
    """Test HTML to TXT conversion."""
    file_content = self.convert_file(
      "<html>héhé</html>".encode(),
      "html",
      "txt",
    )
    self.assertEqual(
      file_content,
      codecs.BOM_UTF8 + b"h\xc3\xa9h\xc3\xa9\n",
    )

  def test_scripting_disabled(self):
    """Test that the basic script raises when scripting is disabled."""
    with self.assertRaisesRegex(Exception, "ooo: scripting is disabled"):
      self.script_test_basic()


def _convert_html_to_text(src_html: bytes, url: str) -> bytes:
  """
  Convert HTML to TXT.

  This is a helper method for using with map.

  Args:
    src_html: HTML to convert.
    url: URL of the CloudOoo server.

  Returns:
    Converted file contents.

  """
  with open_cloudooo_connection(url) as server:
    return convert_file(
      src_html,
      "html",
      "txt",
      server=server,
    )


class TestLibreOfficeCluster(CloudOooTestCase):
  """Class for testing a cluster with multiple backends."""

  __partition_reference__ = "co_cluster"

  @classmethod
  def getInstanceParameterDict(cls) -> Mapping[str, object]:
    return {"backend-count": 4}

  def test_multiple_conversions(self):
    """Test that concurrent requests are distributed in the cluster."""
    pool = multiprocessing.Pool(5)
    with pool:
      converted = pool.map(
        partial(_convert_html_to_text, url=self.url),
        [b"<html><body>hello</body></html>"] * 100,
      )

    self.assertEqual(converted, [codecs.BOM_UTF8 + b"hello\n"] * 100)

    # Haproxy stats are exposed
    res = requests.get(
      urllib_parse.urljoin(self.url, "/haproxy;csv"),
      verify=False,
    )
    reader = csv.DictReader(io.StringIO(res.text))
    line_list = list(reader)
    # Requests have been balanced
    total_hrsp_2xx = {
      line["svname"]: int(line["hrsp_2xx"]) for line in line_list
    }
    self.assertEqual(total_hrsp_2xx["FRONTEND"], 100)
    self.assertEqual(total_hrsp_2xx["BACKEND"], 100)
    for backend in "cloudooo_1", "cloudooo_2", "cloudooo_3", "cloudooo_4":
      # Ideally there should be 25% of requests on each backend, because we use
      # round robin scheduling, but it can happen that some backend take longer
      # to start, so we are tolerant here and just check that each backend
      # process at least one request.
      self.assertGreater(total_hrsp_2xx[backend], 0)
    # No errors
    total_eresp = {
      line["svname"]: int(line["eresp"] or 0) for line in line_list
    }
    self.assertEqual(
      total_eresp,
      {
        "FRONTEND": 0,
        "cloudooo_1": 0,
        "cloudooo_2": 0,
        "cloudooo_3": 0,
        "cloudooo_4": 0,
        "BACKEND": 0,
      },
    )


class TestLibreOfficeScripting(CloudOooTestCase):
  """Class with scripting enabled, to try that functionality."""

  __partition_reference__ = "co_script"

  @classmethod
  def getInstanceParameterDict(cls) -> Mapping[str, object]:
    """Enable scripting for this instance."""
    return {"enable-scripting": True}

  def test_scripting_basic(self):
    """Test that the basic script works."""
    file = self.script_test_basic()
    self.assertEqual(
      file,
      codecs.BOM_UTF8 + b"Hello World\n",
    )
