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


def check_cdn_node_activity_check(log_file, max_age_seconds=300):
  """Check CDN instance node log for recent activity.

  Returns (status, message) where status is 'ok', 'warning', or 'error'.
  """
  import re
  from datetime import datetime

  if not os.path.exists(log_file):
    return ('error',
            'CDN request log file does not exist: %s' % log_file)

  try:
    with open(log_file, 'r') as f:
      lines = f.readlines()
  except IOError as e:
    return ('error',
            'Failed to read CDN request log file %s: %s' % (log_file, e))

  if not lines:
    return ('error',
            'CDN request log file is empty: %s' % log_file)

  log_pattern = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})')
  latest_timestamp = None
  for line in reversed(lines):
    match = log_pattern.match(line.strip())
    if match:
      try:
        latest_timestamp = datetime.strptime(
          match.group(1), '%Y-%m-%d %H:%M:%S')
      except ValueError as e:
        return ('error',
                'Failed to parse timestamp in CDN request log file %s: %s'
                % (log_file, e))
      break

  if latest_timestamp is None:
    return ('error',
            'Could not find a valid timestamp in CDN request log file: %s'
            % log_file)

  now = datetime.now()
  age_seconds = (now - latest_timestamp).total_seconds()

  if age_seconds < 0:
    return ('warning',
            'Latest log entry timestamp is in the future: %s (age: %.1f seconds)'
            % (latest_timestamp.strftime('%Y-%m-%d %H:%M:%S'), age_seconds))

  if age_seconds > max_age_seconds:
    return ('error',
            'CDN request log has no recent activity. '
            'Latest entry is from %s (%.1f minutes ago, threshold: %.1f minutes)'
            % (latest_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
               age_seconds / 60.0, max_age_seconds / 60.0))

  return ('ok',
          'CDN request log is active. Latest entry is from %s (%.1f minutes ago)'
          % (latest_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
             age_seconds / 60.0))


