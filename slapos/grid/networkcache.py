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
import utils
import json
import platform

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
def download_network_cached(cache_url, dir_url, software_url, software_root,
                            key, path, logger, signature_certificate_list):
    """Downloads from a network cache provider

    return True if download succeeded.
    """
    if not LIBNETWORKCACHE_ENABLED:
        return False

    if not(cache_url and dir_url and software_url and software_root):
        return False

    # In order to call nc nicely.
    if len(signature_certificate_list) == 0:
        signature_certificate_list = None
    try:
        nc = NetworkcacheClient(cache_url, dir_url,
            signature_certificate_list=signature_certificate_list)
    except TypeError:
      logger.warning('Incompatible version of networkcache, not using it.')
      return False

    logger.info('Downloading %s binary from network cache.' % software_url)
    try:
        file_descriptor = None
        json_entry_list = nc.select_generic(key)
        for entry in json_entry_list:
            json_information, _ = entry
            try:
                tags = json.loads(json_information)
                if tags.get('machine') != platform.machine():
                    continue
                if tags.get('os') != str(platform.linux_distribution()):
                    continue
                if tags.get('software_url') != software_url:
                    continue
                if tags.get('software_root') != software_root:
                    continue
                sha512 = tags.get('sha512')
                file_descriptor = nc.download(sha512)
                break
            except Exception:
                continue
        if file_descriptor is not None:
            f = open(path, 'w+b')
            try:
                shutil.copyfileobj(file_descriptor, f)
            finally:
                f.close()
                file_descriptor.close()
            return True
    except (IOError, DirectoryNotFound), e:
        logger.info('Failed to download from network cache %s: %s' % \
                                                       (software_url, str(e)))
    return False


@fallback_call
def upload_network_cached(software_root, software_url, cached_key,
    cache_url, dir_url, path, logger, signature_private_key_file,
    shacache_cert_file, shacache_key_file, shadir_cert_file, shadir_key_file):
    """Upload file to a network cache server"""
    if not LIBNETWORKCACHE_ENABLED:
        return False

    if not (software_root and software_url and cached_key \
                          and cache_url and dir_url):
        return False

    logger.info('Uploading %s binary into network cache.' % software_url)

    # YXU: "file" and "urlmd5" should be removed when server side is ready
    kw = dict(
      file="file",
      urlmd5="urlmd5",
      software_url=software_url,
      software_root=software_root,
      machine=platform.machine(),
      os=str(platform.linux_distribution())
    )

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
        return nc.upload_generic(f, cached_key, **kw)
    except (IOError, UploadError), e:
        logger.info('Fail to upload file. %s' % (str(e)))
        return False
    finally:
      f.close()

    return True
