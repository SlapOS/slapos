import caucase.client
import caucase.utils
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from cryptography import x509
from cryptography.hazmat.primitives import serialization


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
  parsed = urllib.parse.urlparse('scheme://' + netloc)
  if ':' in parsed.hostname:
    hostname = '[%s]' % parsed.hostname
  else:
    hostname = parsed.hostname
  return netloc == '%s:%s' % (hostname, parsed.port)


def _check_certificate(url, certificate):
  parsed = urllib.parse.urlparse(url)
  got_certificate = ssl.get_server_certificate((parsed.hostname, parsed.port))
  if certificate.strip() != got_certificate.strip():
    raise ValueError('Certificate for %s does not match expected one' % (url,))


def _get_exposed_csr(url, certificate):
  _check_certificate(url, certificate)
  self_signed = ssl.create_default_context()
  self_signed.check_hostname = False
  self_signed.verify_mode = ssl.CERT_NONE
  return urllib.request.urlopen(url, context=self_signed).read().decode()


def _get_caucase_client(ca_url, ca_crt, user_key):
  return caucase.client.CaucaseClient(
    ca_url=ca_url + '/cas',
    ca_crt_pem_list=caucase.utils.getCertList(ca_crt),
    user_key=user_key,
  )


def _get_caucase_csr_list(ca_url, ca_crt, user_key):
  csr_list = []
  for entry in _get_caucase_client(
    ca_url, ca_crt, user_key).getPendingCertificateRequestList():
    csr = caucase.utils.load_certificate_request(
      caucase.utils.toBytes(entry['csr']))
    csr_list.append({
      'csr_id': entry['id'],
      'csr': csr.public_bytes(serialization.Encoding.PEM).decode()
    })
  return csr_list


def _csr_match(*csr_list):
  number_list = set([])
  for csr in csr_list:
    number_list.add(
      x509.load_pem_x509_csr(csr.encode()).public_key().public_numbers())
  return len(number_list) == 1


def _sign_csr(ca_url, ca_crt, user_key, csr, csr_list):
  signed = False
  client = _get_caucase_client(ca_url, ca_crt, user_key)
  for csr_entry in csr_list:
    if _csr_match(csr, csr_entry['csr']):
      client.createCertificate(int(csr_entry['csr_id']))
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
  ca_url, ca_crt, done_file, user_key, csr_url, \
    csr_url_certificate = sys.argv[1:]
  if _is_done(done_file):
    return
  exposed_csr = _get_exposed_csr(csr_url, csr_url_certificate)
  caucase_csr_list = _get_caucase_csr_list(ca_url, ca_crt, user_key)
  if _sign_csr(
    ca_url, ca_crt, user_key, exposed_csr, caucase_csr_list):
    _mark_done(done_file)
  else:
    print('Failed to sign %s' % (csr_url,))


def caucase_csr_sign_check():
  ca_url, ca_crt, user_key = sys.argv[1:]
  if len(_get_caucase_csr_list(ca_url, ca_crt, user_key)) != 0:
    print('ERR There are CSR to sign on %s' % (ca_url,))
    sys.exit(1)
  else:
    print('OK No CSR to sign on %s' % (ca_url,))
