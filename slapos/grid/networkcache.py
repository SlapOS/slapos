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


import hashlib
import os
import posixpath
import re
import shutil
import urlparse
import traceback

try:
    try:
        from slapos.libnetworkcache import NetworkcacheClient, UploadError, \
          DirectoryNotFound
    except ImportError:
        LIBNETWORKCACHE_ENABLED = False
    else:
        LIBNETWORKCACHE_ENABLED = True
except:
    print 'There was problem while trying to import slapos.libnetworkcache:'\
        '\n%s' % traceback.format_exc()
    LIBNETWORKCACHE_ENABLED = False
    print 'Networkcache forced to be disabled.'

_md5_re = re.compile(r'md5=([a-f0-9]+)')


def _get_md5_from_url(url):
  match = _md5_re.search(url)
  if match:
    return match.group(1)
  return None

def fallback_call(function):
    """Decorator which disallow to have any problem while calling method"""
    def wrapper(self, *args, **kwd):
        """
        Log the call, and the result of the call
        """
        try:
            return function(self, *args, **kwd)
        except: # indeed, *any* exception is swallowed
            print 'There was problem while calling method %r:\n%s' % (
                function.__name__, traceback.format_exc())
            return False
    wrapper.__doc__ = function.__doc__
    return wrapper


@fallback_call
def get_directory_key(url):
    """Returns directory hash based on url.

    Basically check if the url belongs to pypi:
      - if yes, the directory key will be pypi-buildout-urlmd5
      - if not, the directory key will be slapos-buildout-urlmd5
    """
    urlmd5 = hashlib.md5(url).hexdigest()
    if 'pypi' in url:
      return 'pypi-buildout-%s' % urlmd5
    return 'slapos-buildout-%s' % urlmd5


@fallback_call
def download_network_cached(dir_url, cache_url, path, url, logger,
                            signature_certificate_list, md5sum=None):
    """Downloads from a network cache provider

    If something fail (providor be offline, or hash_string fail), we ignore
    network cached files.

    return True if download succeeded.
    """
    if not LIBNETWORKCACHE_ENABLED:
        return False

    if not(dir_url and cache_url):
        return False
    if md5sum is None:
        md5sum = _get_md5_from_url(url)


    directory_key = get_directory_key(url)
    url = os.path.basename(url)

    if len(signature_certificate_list) == 0:
        # convert [] into None in order to call nc nicely
        signature_certificate_list = None
    try:
        nc = NetworkcacheClient(cache_url, dir_url,
            signature_certificate_list=signature_certificate_list)
    except TypeError:
      logger.warning('Incompatible version of networkcache, not using it.')
      return False

    logger.info('Downloading %s from network cache.' % url)
    try:
        file_descriptor = nc.select(directory_key)

        f = open(path, 'w+b')
        try:
            shutil.copyfileobj(file_descriptor, f)
        finally:
            f.close()
            file_descriptor.close()

        if not check_md5sum(path, md5sum):
            logger.info('MD5 checksum mismatch downloading %s' % url)
            return False

    except (IOError, DirectoryNotFound), e:
        logger.info('Failed to download from network cache %s: %s' % \
                                                       (url, str(e)))
        return False
    return True


@fallback_call
def upload_network_cached(dir_url, cache_url, external_url, path, logger,
   signature_private_key_file, shacache_cert_file, shacache_key_file,
   shadir_cert_file, shadir_key_file):
    """Upload file to a network cache server"""
    if not LIBNETWORKCACHE_ENABLED:
        return False

    if not (dir_url and cache_url):
        return False

    logger.info('Uploading %s into network cache.' % external_url)

    file_name = get_filename_from_url(external_url)

    directory_key = get_directory_key(external_url)
    kw = dict(file_name=file_name,
              urlmd5=hashlib.md5(external_url).hexdigest())

    f = open(path, 'r')
    # convert '' into None in order to call nc nicely
    if not signature_private_key_file:
        signature_private_key_file = None
    if not shacache_cert_file:
        shacache_cert_file = None
    if not shacache_key_file:
        shacache_key_file = None
    if not shadir_cert_file:
        shadir_cert_file = None
    if not shadir_key_file:
        shadir_key_file = None
    try:
        nc = NetworkcacheClient(cache_url, dir_url,
            signature_private_key_file=signature_private_key_file,
            shacache_cert_file=shacache_cert_file,
            shacache_key_file=shacache_key_file,
            shadir_cert_file=shadir_cert_file,
            shadir_key_file=shadir_key_file)
    except TypeError:
        logger.warning('Incompatible version of networkcache, not using it.')
        return False

    try:
        return nc.upload(f, directory_key, **kw)
    except (IOError, UploadError), e:
        logger.info('Fail to upload file. %s' % \
                                                  (str(e)))
        return False

    finally:
      f.close()

    return True


@fallback_call
def get_filename_from_url(url):
    """Inspired how pip get filename from url.
    """
    parsed_url = urlparse.urlparse(url)
    if parsed_url.query and parsed_url.path.endswith('/'):
      name = parsed_url.query.split('?', 1)[0]
    elif parsed_url.path.endswith('/') and not parsed_url.query:
      name = parsed_url.path.split('/')[-2]
    else:
      name = posixpath.basename(parsed_url.path)

    name = name.split('#', 1)[0]
    assert name, (
           'URL %r produced no filename' % url)
    return name


from download import check_md5sum
