from __future__ import print_function

import json
import os
import ssl
import subprocess
import sys
import urlparse

class Recipe(object):
  def __init__(self, *args, **kwargs):
    pass

  def install(self):
    return []

  def update(self):
    return self.install()

def validate_netloc(netloc):
  # a bit crazy way to validate that the passed parameter is haproxy
  # compatible server netloc
  parsed = urlparse.urlparse('scheme://'+netloc)
  if ':' in parsed.hostname:
    hostname = '[%s]' % parsed.hostname
  else:
    hostname = parsed.hostname
  return netloc == '%s:%s' % (hostname, parsed.port)


def _check_certificate(url, certificate):
  parsed = urlparse.urlparse(url)
  got_certificate = ssl.get_server_certificate((parsed.hostname, parsed.port))
  if certificate.strip() != got_certificate.strip():
    raise ValueError('Certificate for %s does not match expected one' % (url,))


def _get_exposed_csr(curl, url):
  return subprocess.check_output([curl, '-s', '-k', '-g', url]).strip()


def _get_caucase_csr_list(caucase, user_key):
  return json.loads(subprocess.check_output(
    [caucase, '--list-csr', '--list-csr-style', 'json', '--user-key', user_key]
  ))


def _get_modulus(openssl, csr):
  popen = subprocess.Popen([
    openssl, 'req', '-noout', '-modulus'], stdin=subprocess.PIPE,
    stdout=subprocess.PIPE)
  modulus = popen.communicate(csr)[0]
  if popen.returncode != 0:
    raise ValueError('Failed to get modulus')
  return modulus


def _sign_csr(caucase, openssl, user_key, csr, csr_list):
  signed = False
  for csr_entry in csr_list:
    if _get_modulus(openssl, csr) == _get_modulus(openssl, csr_entry['csr']):
      subprocess.check_call([
        caucase, '--user-key', user_key, '--sign-csr', csr_entry['csr_id']])
      print('Signed csr with id %s' % (csr_entry['csr_id'],))
      signed = True
      break
  return signed


def _mark_done(filename):
  with open(filename, 'w') as fh:
    fh.write('done')
  print('Marked file %s' % (filename,))


def _is_done(filename):
  if os.path.exists(filename):
    return True
  return False


def smart_sign():
  curl, openssl, caucase_wrapper, done_file, user_key, csr_url, \
    csr_url_certificate = sys.argv[1:]
  if _is_done(done_file):
    return
  _check_certificate(csr_url, csr_url_certificate)
  exposed_csr = _get_exposed_csr(curl, csr_url)
  caucase_csr_list = _get_caucase_csr_list(caucase_wrapper, user_key)
  if _sign_csr(
    caucase_wrapper, openssl, user_key, exposed_csr, caucase_csr_list):
    _mark_done(done_file)
  else:
    print('Failed to sign %s' % (csr_url,))
