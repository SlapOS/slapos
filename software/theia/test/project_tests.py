##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
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
from __future__ import unicode_literals

import gzip
import json
import os
import re
import subprocess
import time
import unittest

import requests

from datetime import datetime, timedelta
from six.moves.urllib.parse import urljoin

from slapos.testing.testcase import installSoftwareUrlList

import test


erp5_software_release_url = 'https://lab.nexedi.com/xavier_thompson/slapos/raw/erp5_fix_mariadb_init/software/erp5/software.cfg'


def setUpModule():
  installSoftwareUrlList(
    test.SlapOSInstanceTestCase,
    [test.theia_software_release_url, erp5_software_release_url],
    debug=bool(int(os.environ.get('SLAPOS_TEST_DEBUG', 0))),
  )


class ERP5Mixin(object):
  _test_software_url = erp5_software_release_url
  _regex = re.compile(r"{\s*'_'\s*:\s*'(.*)'\s*}")

  def _getERP5ConnexionParameters(self, software_type='export'):
    slapos = self._getSlapos(software_type)
    out = subprocess.check_output(
      (slapos, 'request', 'test_instance', self._test_software_url),
      stderr=subprocess.STDOUT,
    )
    print(out)
    return json.loads(self._regex.search(out).group(1))

  def _getERP5Url(self, connexion_parameters, path=''):
    return urljoin(connexion_parameters['family-default-v6'], path)

  def _getERP5User(self, connexion_parameters):
    return connexion_parameters['inituser-login']

  def _getERP5Password(self, connexion_parameters):
    return connexion_parameters['inituser-password']

  def _waitERP5connected(self, url, user, password):
    for _ in range(5):
      try:
        resp = requests.get('%s/getId' % url, auth=(user, password), verify=False, allow_redirects=False)
      except Exception:
        time.sleep(20)
        continue
      if resp.status_code != 200:
        time.sleep(20)
        continue
      break
    else:
      self.fail('Failed to connect to ERP5')
    self.assertEqual(resp.text, 'erp5')


class TestTheiaResilienceERP5(ERP5Mixin, test.TestTheiaResilience):
  test_instance_max_retries = 12
  backup_started_tries = 180
  backup_finished_tries = 180
  backup_wait_interval = 60

  def _prepareExport(self):
    super(TestTheiaResilienceERP5, self)._prepareExport()

    # Connect to erp5
    info = self._getERP5ConnexionParameters()
    user = self._getERP5User(info)
    password = self._getERP5Password(info)
    url = self._getERP5Url(info, 'erp5')
    self._waitERP5connected(url, user, password)

    # Change title
    new_title = time.strftime("Couscous %a %d %b %Y %H:%M:%S", time.localtime(time.time()))
    requests.get('%s/portal_types/setTitle?value=%s' % (url, new_title), auth=(user, password), verify=False)
    resp = requests.get('%s/portal_types/getTitle' % url, auth=(user, password), verify=False, allow_redirects=False)
    self.assertEqual(resp.text, new_title)
    self._erp5_new_title = new_title

    # Wait until changes have been catalogued
    mariadb_partition = self._getTypePartitionPath('export', 'srv', 'runner', 'instance', 'slappart3')
    mysql_bin = os.path.join(mariadb_partition, 'bin', 'mysql')
    wait_activities_script = os.path.join(
      mariadb_partition, 'software_release', 'parts', 'erp5',
      'Products', 'CMFActivity', 'bin', 'wait_activities')
    subprocess.check_call((wait_activities_script, 'erp5'), env={'MYSQL': mysql_bin})

    # Check that changes have been catalogued
    output = subprocess.check_output((mysql_bin, 'erp5', '-e', 'SELECT title FROM catalog WHERE id="portal_types"'))
    self.assertIn(new_title, output)

    # Compute backup date in the near future
    soon = (datetime.now() + timedelta(minutes=2)).replace(second=0)
    date = '*:%d:00' % soon.minute
    params = '_={"zodb-zeo": {"backup-periodicity": "%s"}, "mariadb": {"backup-periodicity": "%s"} }' % (date, date)

    # Update ERP5 parameters
    print('Requesting EPR5 with parameters %s' % params)
    slapos = self._getSlapos()
    subprocess.check_call((slapos, 'request', 'test_instance', self._test_software_url, '--parameters', params))

    # Process twice to propagate parameter changes
    for _ in range(2):
      subprocess.check_call((slapos, 'node', 'instance'))

    # Restart cron (actually all) services to let them take the new date into account
    # XXX this should not be required, updating ERP5 parameters should be enough
    subprocess.call((slapos, 'node', 'restart', 'all'))

    # Wait until after the programmed backup date, and a bit more
    t = (soon - datetime.now()).total_seconds()
    self.assertLess(0, t)
    time.sleep(t + 120)

    # Check that backup has started
    export_instance_dir = self._getTypePartitionPath('export', 'srv', 'runner', 'instance')
    mariadb_backup = os.path.join(export_instance_dir, 'slappart3', 'srv', 'backup', 'mariadb-full')
    zodb_backup = os.path.join(export_instance_dir, 'slappart4', 'srv', 'backup', 'zodb', 'root')
    mariadb_backup_dump, = os.listdir(mariadb_backup)
    self.assertEqual(len(os.listdir(zodb_backup)), 3)

    # Check that mariadb catalog backup contains expected changes
    with gzip.open(os.path.join(mariadb_backup, mariadb_backup_dump)) as f:
      self.assertIn(new_title, f.read(), "Mariadb catalog backup %s is not up to date" % mariadb_backup_dump)

  def _checkTakeover(self):
    super(TestTheiaResilienceERP5, self)._checkTakeover()

    # Connect to erp5
    info = self._getERP5ConnexionParameters()
    user = self._getERP5User(info)
    password = self._getERP5Password(info)
    url = self._getERP5Url(info, 'erp5')
    self._waitERP5connected(url, user, password)

    resp = requests.get('%s/portal_types/getTitle' % url, auth=(user, password), verify=False, allow_redirects=False)
    self.assertEqual(resp.text, self._erp5_new_title)

    # Check that the mariadb catalog is not yet restored
    mariadb_partition = self._getTypePartitionPath('export', 'srv', 'runner', 'instance', 'slappart3')
    mysql_bin = os.path.join(mariadb_partition, 'bin', 'mysql')
    query = 'SELECT title FROM catalog WHERE id="portal_types"'
    try:
      out = subprocess.check_output((mysql_bin, 'erp5', '-e', query))
    except subprocess.CalledProcessError:
      out = ''
    self.assertNotIn(self._erp5_new_title, out)

    # Stop all services
    slapos = self._getSlapos()
    print("Stop all services")
    subprocess.call((slapos, 'node', 'stop', 'all'))

    # Manually restore mariadb from backup
    mariadb_restore_script = os.path.join(mariadb_partition, 'bin', 'restore-from-backup')
    print("Restore mariadb from backup")
    subprocess.check_call(mariadb_restore_script)

    # Check that the test instance is properly redeployed after restoring mariadb
    # This restarts the services and checks the promises of the test instance
    # Process twice to propagate state change
    for _ in range(2):
      self._processEmbeddedInstance(self.test_instance_max_retries)

    # Check that the mariadb catalog was properly restored
    out = subprocess.check_output((mysql_bin, 'erp5', '-e', query))
    self.assertIn(self._erp5_new_title, out, 'Mariadb catalog is not properly restored')
