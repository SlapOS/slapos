##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
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

import functools
import http.server
import threading


class _QuietRequestHandler(http.server.SimpleHTTPRequestHandler):
  def log_message(self, format, *args):
    pass


class CheckoutHTTPServer:
  """Serve a source checkout over HTTP, so a Software Release builds the
  way production consumes it — ${:_profile_base_location_} is a URL, not
  a directory."""

  def __init__(self, directory, ip, port):
    self._directory = directory
    self._ip = ip
    self._port = port
    self._server = None
    self._thread = None

  @property
  def url(self):
    return 'http://%s:%s' % (self._ip, self._port)

  def start(self):
    self._server = http.server.ThreadingHTTPServer(
      (self._ip, self._port),
      functools.partial(_QuietRequestHandler, directory=self._directory))
    self._thread = threading.Thread(
      target=self._server.serve_forever, daemon=True)
    self._thread.start()

  def stop(self):
    if self._server is None:
      return
    self._server.shutdown()
    self._server.server_close()
    self._thread.join()
    self._server = None
    self._thread = None
