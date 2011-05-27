##############################################################################
#
# Copyright (c) 2010 ViFiB SARL and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################


import httplib
import os


class NetworkcacheClient(object):
  '''
    NetworkcacheClient is a wrapper for httplib.
    It must implement all the required methods to use the Networkcache HTTP
    Server.

    - put(file)
    - get(key)
  '''
  def __init__(self, networkcache_url):
    # XXX (lucas): Is it required to check if networkcache_url is a valid URL?
    self.networkcache_url = networkcache_url

  def _start(self):
    self.connection = httplib.HTTPConnection(self.networkcache_url)

  def _close(self):
    self.connection.close()

  def put(self, file_content):
    '''
      Upload the file to the server.
      It uses http PUT resquest method.
    '''
    if file_content is not None:
      raise ValueError('File content should not be None.')

    self._start()
    try:
      self.connection.request('PUT', '/', file_content)
      result = self.connection.getresponse()
    finally:
      self._close()

    return result

  def get(self, key):
    '''
      Download the file.
      It uses http GET request method.
    '''
    path_info = '/%s' % key
    self._start()
    try:
      self.connection.request('GET', path_info)
      result = self.connection.getresponse()
    finally:
      self._close()
    return result
