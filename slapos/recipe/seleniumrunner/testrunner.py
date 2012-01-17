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

from erp5functionaltestreporthandler import ERP5TestReportHandler
from ERP5TypeFunctionalTestCase import Xvfb, Firefox, TimeoutError
from time import sleep
import time
import os
import urllib2

def run(args):
  config = args[0]

  test_url = assembleTestUrl(config['base_url'], config['suite_name'],
      config['user'], config['password'])

  # There is no test that can take more them 24 hours
  timeout = 2.0 * 60 * 60
  
  while True:
    erp5_report = ERP5TestReportHandler(config['test_report_instance_url'],
        config['project'] + '@' + config['suite_name'])
    # Clean old test results if any
    openUrl('%s/TestTool_cleanUpTestResults?__ac_name=%s&__ac_password=%s' % (
        config['base_url'], config['user'], config['password']))
    if getStatus(config['base_url']) is not '':
      print("ERROR : Impossible to clean old test result(s)")
    else:
      # Environment is ready, we launch test.
      os.environ['DISPLAY'] = config['display']
      xvfb = Xvfb(config['etc_directory'], config['xvfb_binary'])
      profile_dir = os.path.join(config['etc_directory'], 'profile')
      browser = Firefox(profile_dir, config['base_url'], config['browser_binary'])
      try:
        start = time.time()
        xvfb.run()
        profile_dir = os.path.join(config['etc_directory'], 'profile')
        browser.run(test_url , xvfb.display)
        erp5_report.reportStart()
        while getStatus(config['base_url']) is '':
          time.sleep(10)
          if (time.time() - start) > float(timeout):
            raise TimeoutError("Test took more them %s seconds" % timeout)
      except TimeoutError:
        continue
      finally:
        browser.quit()
        xvfb.quit()
      
      erp5_report.reportFinished(getStatus(config['base_url']).encode("utf-8",
          "replace"))
      
      # Clean test results for next test
      openUrl('%s/TestTool_cleanUpTestResults?__ac_name=%s&__ac_password=%s' % (
          config['base_url'], config['user'], config['password']))
      
      print("Test finished and report sent, sleeping.")
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

def getStatus(url):
    try:
      status = openUrl('%s/portal_tests/TestTool_getResults' % (url))
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
