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

from datetime import datetime
from erp5functionaltestreporthandler import ERP5TestReportHandler
from ERP5TypeFunctionalTestCase import TimeoutError
from time import sleep
import time
import os
import urllib2
import urlparse
from subprocess import Popen, PIPE
import signal

def run(args):
  suite_url = args[0]
  report_url = args[1]
  project = args[2]
  browser_binary = args[3]

  suite_parsed = urlparse.urlparse(suite_url)

  config = {
    'suite_name': suite_parsed.path.split('/')[-1],
    'base_url': "%s://%s%s" % (suite_parsed.scheme, suite_parsed.hostname,
                               '/'.join(suite_parsed.path.split('/')[:-1])),
    'user': suite_parsed.username,
    'password': suite_parsed.password,
    }

  test_url = assembleTestUrl(config['base_url'], config['suite_name'],
      config['user'], config['password'])

  # There is no test that can take more them 24 hours
  timeout = 2.0 * 60 * 60

  while True:
    erp5_report = ERP5TestReportHandler(report_url,
        project + '@' + config['suite_name'])
    try:
      try:
        start = time.time()
        print("Running test on: %s" % test_url)
        process = Popen('%s "%s"' % (browser_binary, test_url),
                        stdout=PIPE,
                        stderr=PIPE,
                        shell=True,
                        close_fds=True)
        erp5_report.reportStart()
        while not isTestFinished(config['base_url']):
          time.sleep(10)
          print("Test not finished yet.")
          if (time.time() - start) > float(timeout):
            raise TimeoutError("Test took more than %s seconds" % timeout)
      except TimeoutError:
        continue
      finally:
        if process.pid:
          os.kill(process.pid, signal.SIGTERM)
      print("Test has finished and Firefox has been killed.")

      erp5_report.reportFinished(getStatus(config['base_url']).encode("utf-8",
          "replace"))


      print("Test finished and report sent, sleeping.")
    except urllib2.URLError, urlError:
        print "Error: %s" % urlError.msg
    sleep(3600)

def openUrl(url):
    # Send Accept-Charset headers to activate the UnicodeConflictResolver
    # (imitating firefox 3.5.9 here)
    headers = { 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7' }
    request = urllib2.Request(url, headers=headers)
    # Try to use long timeout, this is needed when there is many
    # activities runing
    try:
      f = urllib2.urlopen(request, timeout=3600*4)
    except TypeError:
      f = urllib2.urlopen(request)
    file_content = f.read()
    f.close()
    return file_content

def isTestFinished(url):
  """Fetch latest report. If report has been created less than 60 seconds ago,
  it must be the current one.
  Return true if test is finished, else return false.
  """
  latest_report = openUrl('%s/portal_tests/TestTool_getLatestReportId/' % url)
  if latest_report is '':
    return False
  latest_report_date = latest_report[7:]
  time_delta = datetime.now() - \
      datetime.strptime(latest_report_date, '%Y%m%d_%H%M%S' )
  if time_delta.days is not 0:
    return False
  if time_delta.seconds < 120:
    return True
  return False

def getStatus(url):
    try:
      # Try 5 times.
      for i in range(5):
        try:
          status = openUrl('%s/portal_tests/TestTool_getResults/' % (url))
          break
        except urllib2.URLError, urlError:
          if i is 4: raise
          print("Warning : %s while getting status" % urlError.msg)
    except urllib2.HTTPError, e:
      if e.msg == "No Content":
        status = ""
      else:
        raise
    return status

def assembleTestUrl(base_url, suite_name, user, password):
      """
      Create the full url to the testrunner
      """
      test_url = "%s/%s/core/TestRunner.html?test=../test_suite_html&"\
          "resultsUrl=%s/postResults&auto=on&__ac_name=%s&__ac_password=%s" % (
          base_url, suite_name, base_url, user, password)
      return test_url
