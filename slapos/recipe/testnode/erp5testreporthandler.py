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

  def reportFinished(self, out_file, revision, success, duration, text):
    # make file parsable by erp5_test_results
    tempcmd = tempfile.mkstemp()[1]
    tempcmd2 = tempfile.mkstemp()[1]
    tempout = tempfile.mkstemp()[1]
    templog = tempfile.mkstemp()[1]
    log_lines = open(out_file, 'r').readlines()
    tl = open(templog, 'w')
    tl.write(TB_SEP + '\n')
    if len(log_lines) > 900:
      tl.write('...[truncated]... \n\n')
    for log_line in log_lines[-900:]:
      starts = log_line.startswith
      if starts('Ran') or starts('FAILED') or starts('OK') or starts(TB_SEP):
        continue
      if starts('ERROR: ') or starts('FAIL: '):
        tl.write('internal-test: ' + log_line)
        continue
      tl.write(log_line)

    tl.write("----------------------------------------------------------------------\n")
    tl.write('Ran 1 test in %.2fs\n' % duration)
    if success:
      tl.write('OK\n')
    else:
      tl.write('FAILED (failures=1)\n')
    tl.write(TB_SEP + '\n')
    tl.close()
    open(tempcmd, 'w').write("""svn info dummy""")
    open(tempcmd2, 'w').write(self.suite_name)
    open(tempout, 'w').write("Revision: %s\n%s" % (revision, text))
    # create nice zip archive
    tempzip = tempfile.mkstemp()[1]
    zip = zipfile.ZipFile(tempzip, 'w')
    zip.write(tempcmd, 'dummy/001/cmdline')
    zip.write(tempout, 'dummy/001/stdout')
    zip.write(templog, 'dummy/001/stderr')
    zip.write(tempout, '%s/002/stdout' % self.suite_name)
    zip.write(templog, '%s/002/stderr' % self.suite_name)
    zip.write(tempcmd2, '%s/002/cmdline' % self.suite_name)
    zip.close()
    os.unlink(templog)
    os.unlink(tempcmd)
    os.unlink(tempout)
    os.unlink(tempcmd2)

    # post it to ERP5
    self.connection_helper.POST('TestResultModule_reportCompleted', dict(
      test_report_id=self.test_id),
      file_list=[('filepath', tempzip)]
      )
    os.unlink(tempzip)
