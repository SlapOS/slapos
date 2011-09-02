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
from time import sleep
import os
from subprocess import Popen, PIPE
from re import search
import urllib2

def run(args):
  config = args[0]

  test_url = assembleTestUrl(config['base_url'], config['user'], config['password'])

  while True:
    erp5_report = ERP5TestReportHandler(test_url, config['suite_name'])   

    xvfb = Popen([config['xvfb_binary'], config['display']], stdout=PIPE)
    os.environ['DISPLAY'] = config['display']
    sleep(10)

    command = []
    command.append(config['browser_binary'])
    command.append(config['option_ssl'])
    command.append(config['option_translate'])
    command.append(config['option_security'])
    command.append(test_url)

    chromium = Popen(command, stdout=PIPE)
    erp5_report.reportStart()
    sleep(10)
            
    #while getStatus(config['base_url']) is None:
    #  sleep(10)
    
   #erp5_report.reportFinished(getStatus(config['base_url']).encode("utf-8", "replace"))
            
    chromium.kill()
    terminateXvfb(xvfb, config['display'])
    sleep(10)

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
      if e.msg == "No Content" :
        status = ""
      else:
        raise
    return status

def assembleTestUrl(base_url, user, password):
      """
      Create the full url to the testrunner
      """
           
      test_url = "%s/core/TestRunner.html?test=../test_suite_html&resultsUrl=%s/postResults&auto=on&__ac_name=%s&__ac_password=%s" % (base_url, base_url, user, password)

      return test_url

def terminateXvfb(process, display):
  process.kill()
  lock_filepath = '/tmp/.X%s-lock' % display.replace(":", "")                                                                                       
  if os.path.exists(lock_filepath):                                                                                                                 
    os.system('rm %s' % lock_filepath)
  
