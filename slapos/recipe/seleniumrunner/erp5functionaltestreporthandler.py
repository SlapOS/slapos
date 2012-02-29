##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
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
#############################################################################

import re
import urlparse
import urllib
import httplib
import mimetools
from random import randint
import tempfile
import os
import stat
import zipfile
import mimetypes
import datetime

TB_SEP = "============================================================="\
    "========="

# REGEX FOR ZELENIUM TESTS
TEST_PASS_RE = re.compile('<th[^>]*>Tests passed</th>\n\s*<td[^>]*>([^<]*)')
TEST_FAILURE_RE = re.compile('<th[^>]*>Tests failed</th>\n\s*<td[^>]*>([^<]*)')
IMAGE_RE = re.compile('<img[^>]*?>')
TEST_ERROR_TITLE_RE = re.compile('(?:error.gif.*?>|title status_failed"><td[^>]*>)([^>]*?)</td></tr>', re.S)
TEST_RESULT_RE = re.compile('<div style="padding-top: 10px;">\s*<p>\s*'
                          '<img.*?</div>\s.*?</div>\s*', re.S)
DURATION_RE = re.compile('<th[^>]*>Elapsed time \(sec\)</th>\n\s*<td[^>]*>([^<]*)')

TEST_ERROR_RESULT_RE = re.compile('.*(?:error.gif|title status_failed).*', re.S)

def get_content_type(f):
  return mimetypes.guess_type(f.name)[0] or 'application/octet-stream'

class ConnectionHelper:
  def __init__(self, url):
    self.conn = urlparse.urlparse(url)
    if self.conn.scheme == 'http':
      connection_type = httplib.HTTPConnection
      if self.conn.port is None:
        self.port = 80
    else:
      connection_type = httplib.HTTPSConnection
      if self.conn.port is None:
        self.port = 443
    self.connection_type = connection_type

  def _connect(self):
    self.connection = self.connection_type(self.conn.hostname + ':' +
        str(self.conn.port or self.port))

  def POST(self, path, parameter_dict, file_list=None):
    self._connect()
    parameter_dict.update(__ac_name=self.conn.username,
                          __ac_password=self.conn.password)
    header_dict = {'Content-type': "application/x-www-form-urlencoded"}
    if file_list is None:
      body = urllib.urlencode(parameter_dict)
    else:
      boundary = mimetools.choose_boundary()
      header_dict['Content-type'] = 'multipart/form-data; boundary=%s' % (
          boundary,)
      body = ''
      for k, v in parameter_dict.iteritems():
        body += '--%s\r\n' % boundary
        body += 'Content-Disposition: form-data; name="%s"\r\n' % k
        body += '\r\n'
        body += '%s\r\n' % v
      for name, filename in file_list:
        f = open(filename, 'r')
        body += '--%s\r\n' % boundary
        body += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'\
                % (name, name)
        body += 'Content-Type: %s\r\n' % get_content_type(f)
        body += 'Content-Length: %d\r\n' % os.fstat(f.fileno())[stat.ST_SIZE]
        body += '\r\n'
        body += f.read()
        f.close()
        body += '\r\n'
    self.connection.request("POST", self.conn.path + '/' + path,
          body, header_dict)
    self.response = self.connection.getresponse()


class ERP5TestReportHandler:
  def __init__(self, url, suite_name):
    # random test id
    self.test_id = "%s-%X" % (
       ("%s" % datetime.date.today()).replace("-", ""),
       randint(1, 10000000000000000),
     )
    self.connection_helper = ConnectionHelper(url)
    self.suite_name = suite_name

  def reportStart(self):
    # report that test is running
    print 'Starting test with id %s' % self.test_id
    self.connection_helper.POST('TestResultModule_reportRunning', dict(
      test_suite=self.suite_name,
      test_report_id=self.test_id,
      ))

  def reportFinished(self, out_file):
    # make file parsable by erp5_test_results
    out_file, success, failure, duration = self.processResult(out_file)

    # XXX-Cedric : make correct display in test_result_module
    tempcmd = tempfile.mkstemp()[1]
    tempcmd2 = tempfile.mkstemp()[1]
    tempout = tempfile.mkstemp()[1]
    templog = tempfile.mkstemp()[1]
    tl = open(templog, 'w')
    tl.write(TB_SEP + '\n')
    tl.write(out_file)

    tl.write("----------------------------------------------------------------------\n")
    tl.write('Ran 1 test in %.2fs\n' % duration)
    if success:
      tl.write('OK\n')
    else:
      tl.write('FAILED (failures=1)\n')
    tl.write(TB_SEP + '\n')
    tl.close()
    open(tempcmd, 'w').write(""" %s""" % self.suite_name)
    # create nice zip archive
    tempzip = tempfile.mkstemp()[1]
    # XXX-Cedric : support multiple tests
    zip = zipfile.ZipFile(tempzip, 'w')
    zip.write(tempout, '%s/001/stdout' % self.suite_name)
    zip.write(templog, '%s/001/stderr' % self.suite_name)
    zip.write(tempcmd, '%s/001/cmdline' % self.suite_name)
    zip.close()
    os.unlink(templog)
    os.unlink(tempcmd)
    os.unlink(tempout)
    os.unlink(tempcmd2)

    # post it to ERP5
    self.connection_helper.POST('TestResultModule_reportCompleted',
        dict(test_report_id=self.test_id), file_list=[('filepath', tempzip)])
    os.unlink(tempzip)

  def processResult(self, out_file):
    file_content = out_file
    sucess_amount = TEST_PASS_RE.search(file_content).group(1)
    failure_amount = TEST_FAILURE_RE.search(file_content).group(1)
    error_title_list = [re.compile('\s+').sub(' ', x).strip()
                    for x in TEST_ERROR_TITLE_RE.findall(file_content)]
    duration = DURATION_RE.search(file_content).group(1)
    detail = ''
    for test_result in TEST_RESULT_RE.findall(file_content):
      if  TEST_ERROR_RESULT_RE.match(test_result):
        detail += test_result

    detail = IMAGE_RE.sub('', detail)
    if detail:
      detail = IMAGE_RE.sub('', detail)
      detail = '''<html>
<head>
 <style type="text/css">tr.status_failed { background-color:red };</style>
</head>
<body>%s</body>
</html>''' % detail
    return detail, int(sucess_amount), int(failure_amount), float(duration)
