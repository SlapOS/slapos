# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2018 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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

import subprocess
import functools
import signal
import traceback
from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

class WrapPromise(GenericPromise):
  """
    A wrapper promise used to run old promises style and bash promises
  """

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    self.setPeriodicity(minute=2)

  @staticmethod
  def terminate(name, logger, process, signum, frame):
    if signum in [signal.SIGINT, signal.SIGTERM] and process.poll() is None:
      logger.info("Terminating promise process %r" % name)
      try:
        # make sure we kill the process on timeout
        process.terminate()
      except Exception:
        logger.error(traceback.format_exc())

  def sense(self):
    promise_process = subprocess.Popen(
        [self.getPromiseFile()],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=self.getPartitionFolder()
    )
    handler = functools.partial(self.terminate, self.getName(), self.logger,
                                promise_process)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    output, error = promise_process.communicate()
    message = output or ""
    if error:
      message += "\n" + error
    if promise_process.returncode != 0:
      self.logger.error(message.strip())
    else:
      self.logger.info(message.strip())

  def test(self):
    # Fail if the latest promise result failed
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    # Fail if 3 latest promise result failed, no bang
    return self._test(result_count=3, failure_amount=3)
