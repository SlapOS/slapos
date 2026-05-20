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


_EPM_HTTP_REASONS = {
  '400': 'Bad Request',
  '404': 'Not Found',
  '408': 'Request Timeout',
  '500': 'Internal Server Error',
  '502': 'Bad Gateway',
  '503': 'Service Unavailable',
  '504': 'Gateway Timeout',
}


def _haproxy_format(code, html):
  reason = _EPM_HTTP_REASONS[code]
  body = html.encode('utf-8')
  header = (
    f'HTTP/1.0 {code} {reason}\r\n'
    f'Cache-Control: no-cache\r\n'
    f'Connection: close\r\n'
    f'Content-Type: text/html; charset=utf-8\r\n'
    f'Content-Length: {len(body)}\r\n'
    f'\r\n'
  )
  return header + html


def error_page_manager_main():
  import hashlib
  import http.server
  import json
  import logging
  import os
  import socket
  import ssl
  import sys
  import threading

  with open(sys.argv[1]) as f:
    config = json.load(f)

  logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
      logging.FileHandler(config['log_file']),
      logging.StreamHandler(sys.stdout),
    ],
  )
  logger = logging.getLogger('error-page-manager')

  IP = config['ip']
  PORT = config['port']
  CERTIFICATE = config['certificate']
  KEY = config['key']
  ERROR_PAGES_DIR = os.path.normpath(config['error_pages_dir'])
  BUILTIN_DIR = os.path.normpath(config['builtin_dir'])

  READ_TOKEN = open(config['read_token_file']).read().strip()
  OPERATOR_TOKEN = open(config['operator_token_file']).read().strip()
  SLAVE_TOKEN_MAP = {
    open(token_file).read().strip(): slave_reference
    for slave_reference, token_file in config['slave_token_files']
  }

  SUPPORTED_CODES = ['400', '404', '408', '500', '502', '503', '504']
  SLAVE_CODES = ['502', '503', '504']

  _lock = threading.Lock()

  def _read_html(path):
    if os.path.isfile(path):
      with open(path, encoding='utf-8') as f:
        return f.read()
    return None

  def _sha256(path):
    if not os.path.isfile(path):
      return None
    with open(path, 'rb') as f:
      return hashlib.sha256(f.read()).hexdigest()

  def _refresh_haproxy_file(slot, code):
    if slot == 'cluster':
      haproxy_dir = os.path.join(ERROR_PAGES_DIR, 'haproxy', 'cluster')
    else:
      haproxy_dir = os.path.join(ERROR_PAGES_DIR, 'haproxy', 'slaves', slot)
    os.makedirs(haproxy_dir, exist_ok=True)
    haproxy_path = os.path.join(haproxy_dir, f'{code}.http')

    if slot == 'cluster':
      html = _read_html(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'))
    else:
      html = _read_html(os.path.join(ERROR_PAGES_DIR, 'slaves', slot, f'{code}.html'))
      if html is None:
        html = _read_html(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'))

    if html is None:
      html = _read_html(os.path.join(BUILTIN_DIR, f'{code}.html'))

    with open(haproxy_path, 'w', encoding='utf-8') as f:
      f.write(_haproxy_format(code, html))

  def _refresh_all_for_code(code):
    _refresh_haproxy_file('cluster', code)
    slaves_dir = os.path.join(ERROR_PAGES_DIR, 'haproxy', 'slaves')
    if os.path.isdir(slaves_dir):
      for ref in os.listdir(slaves_dir):
        if code in SLAVE_CODES:
          _refresh_haproxy_file(ref, code)

  def _build_manifest():
    manifest = {}
    haproxy_dir = os.path.join(ERROR_PAGES_DIR, 'haproxy')
    for dirpath, _, filenames in os.walk(haproxy_dir):
      for fname in filenames:
        full = os.path.join(dirpath, fname)
        rel = os.path.relpath(full, haproxy_dir)
        sha = _sha256(full)
        if sha:
          manifest[rel] = sha
    return manifest

  def _web_ui():
    rows = ''
    for code in SUPPORTED_CODES:
      op_file = os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html')
      html = (_read_html(op_file) or '').replace('&', '&amp;').replace('<', '&lt;')
      rows += f'''
        <tr>
          <td class="code">{code}</td>
          <td><textarea name="html_{code}" rows="6">{html}</textarea></td>
          <td>
            <button type="submit" name="action" value="save_{code}">Save</button>
            <button type="submit" name="action" value="reset_{code}">Reset</button>
          </td>
        </tr>'''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Error Page Manager</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; background: #f7f8fa; }}
    h1 {{ margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff;
             box-shadow: 0 1px 4px rgba(0,0,0,.08); border-radius: 6px; overflow: hidden; }}
    th, td {{ padding: .75rem 1rem; text-align: left; border-bottom: 1px solid #eef0f3; }}
    th {{ background: #f0f2f5; font-size: .85rem; color: #555; }}
    td.code {{ font-weight: 700; font-size: 1.1rem; color: #555; white-space: nowrap; }}
    textarea {{ width: 100%; font-family: monospace; font-size: .85rem;
                border: 1px solid #dde; border-radius: 4px; padding: .4rem; resize: vertical; }}
    button {{ padding: .3rem .8rem; border: none; border-radius: 4px; cursor: pointer; margin: .15rem 0; }}
    button[value^="save"] {{ background: #4a90d9; color: #fff; }}
    button[value^="reset"] {{ background: #e0e4ea; color: #333; }}
  </style>
</head>
<body>
  <h1>Error Page Manager</h1>
  <form method="post">
    <table>
      <thead><tr><th>Code</th><th>HTML Content</th><th>Actions</th></tr></thead>
      <tbody>{rows}
      </tbody>
    </table>
  </form>
</body>
</html>'''

  class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
      logger.info(fmt % args)

    def _send(self, code, body, content_type='text/plain'):
      if isinstance(body, str):
        body = body.encode()
      self.send_response(code)
      self.send_header('Content-Type', content_type)
      self.send_header('Content-Length', len(body))
      self.end_headers()
      self.wfile.write(body)

    def _send_json(self, data, code=200):
      self._send(code, json.dumps(data), 'application/json')

    def _read_body(self):
      length = int(self.headers.get('Content-Length', 0))
      if length > 2 * 1024 * 1024:  # 2 MB limit
        return None
      return self.rfile.read(length).decode('utf-8', errors='replace')

    def _parse_path(self):
      parts = self.path.lstrip('/').split('/', 2)
      section = parts[0] if parts else ''
      token = parts[1] if len(parts) > 1 else ''
      rest = parts[2] if len(parts) > 2 else ''
      return section, token, rest

    def do_GET(self):
      section, token, rest = self._parse_path()
      if section == 'sync':
        if token != READ_TOKEN:
          self._send(401, 'Unauthorized')
          return
        with _lock:
          self._send_json(_build_manifest())
      elif section == 'haproxy':
        if token != READ_TOKEN:
          self._send(401, 'Unauthorized')
          return
        full = os.path.normpath(
          os.path.join(ERROR_PAGES_DIR, 'haproxy', rest))
        if not full.startswith(ERROR_PAGES_DIR + os.sep + 'haproxy' + os.sep):
          self._send(403, 'Forbidden')
          return
        if not os.path.isfile(full):
          self._send(404, 'Not found')
          return
        with open(full, 'rb') as f:
          self._send(200, f.read(), 'application/octet-stream')
      elif section == 'operator':
        if token != OPERATOR_TOKEN:
          self._send(401, 'Unauthorized')
          return
        if not rest:
          self._send(200, _web_ui(), 'text/html')
        elif rest in SUPPORTED_CODES:
          op_file = os.path.join(ERROR_PAGES_DIR, 'operator', f'{rest}.html')
          self._send(200, _read_html(op_file) or '', 'text/html')
        else:
          self._send(404, 'Unknown code')
      else:
        self._send(404, 'Not found')

    def do_POST(self):
      section, token, rest = self._parse_path()
      if section != 'operator' or token != OPERATOR_TOKEN:
        self._send(401, 'Unauthorized')
        return
      import urllib.parse
      body = self._read_body()
      if body is None:
        self._send(413, 'Too large')
        return
      params = urllib.parse.parse_qs(body, keep_blank_values=True)
      action = params.get('action', [''])[0]
      if action.startswith('save_'):
        code = action[5:]
        if code not in SUPPORTED_CODES:
          self._send(400, 'Unknown code')
          return
        html = params.get(f'html_{code}', [''])[0]
        with _lock:
          os.makedirs(os.path.join(ERROR_PAGES_DIR, 'operator'), exist_ok=True)
          with open(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'), 'w') as f:
            f.write(html)
          _refresh_all_for_code(code)
      elif action.startswith('reset_'):
        code = action[6:]
        if code not in SUPPORTED_CODES:
          self._send(400, 'Unknown code')
          return
        with _lock:
          op_file = os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html')
          if os.path.exists(op_file):
            os.unlink(op_file)
          _refresh_all_for_code(code)
      self.send_response(303)
      self.send_header('Location', self.path.rsplit('/', 1)[0] + '/')
      self.end_headers()

    def do_PUT(self):
      section, token, rest = self._parse_path()
      if section == 'operator':
        if token != OPERATOR_TOKEN:
          self._send(401, 'Unauthorized')
          return
        code = rest
        if code not in SUPPORTED_CODES:
          self._send(400, 'Unknown code')
          return
        html = self._read_body()
        if html is None:
          self._send(413, 'Too large')
          return
        with _lock:
          os.makedirs(os.path.join(ERROR_PAGES_DIR, 'operator'), exist_ok=True)
          with open(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'), 'w') as f:
            f.write(html)
          _refresh_all_for_code(code)
        self._send(204, '')
      elif section == 'slave':
        ref = SLAVE_TOKEN_MAP.get(token)
        if ref is None:
          self._send(401, 'Unauthorized')
          return
        code = rest
        if code not in SLAVE_CODES:
          self._send(400, f'Slaves may only set: {", ".join(SLAVE_CODES)}')
          return
        html = self._read_body()
        if html is None:
          self._send(413, 'Too large')
          return
        with _lock:
          slave_dir = os.path.join(ERROR_PAGES_DIR, 'slaves', ref)
          os.makedirs(slave_dir, exist_ok=True)
          with open(os.path.join(slave_dir, f'{code}.html'), 'w') as f:
            f.write(html)
          _refresh_haproxy_file(ref, code)
        self._send(204, '')
      else:
        self._send(404, 'Not found')

    def do_DELETE(self):
      section, token, rest = self._parse_path()
      if section == 'operator':
        if token != OPERATOR_TOKEN:
          self._send(401, 'Unauthorized')
          return
        code = rest
        if code not in SUPPORTED_CODES:
          self._send(400, 'Unknown code')
          return
        with _lock:
          op_file = os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html')
          if os.path.exists(op_file):
            os.unlink(op_file)
          _refresh_all_for_code(code)
        self._send(204, '')
      elif section == 'slave':
        ref = SLAVE_TOKEN_MAP.get(token)
        if ref is None:
          self._send(401, 'Unauthorized')
          return
        code = rest
        if code not in SLAVE_CODES:
          self._send(400, f'Slaves may only set: {", ".join(SLAVE_CODES)}')
          return
        with _lock:
          slave_file = os.path.join(ERROR_PAGES_DIR, 'slaves', ref, f'{code}.html')
          if os.path.exists(slave_file):
            os.unlink(slave_file)
          _refresh_haproxy_file(ref, code)
        self._send(204, '')
      else:
        self._send(404, 'Not found')

  class HTTPServerIPv6(http.server.HTTPServer):
    address_family = socket.AF_INET6

  with _lock:
    for code in SUPPORTED_CODES:
      _refresh_haproxy_file('cluster', code)
    for ref in set(SLAVE_TOKEN_MAP.values()):
      for code in SLAVE_CODES:
        _refresh_haproxy_file(ref, code)
  logger.info('Initialized haproxy error files')

  ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  ctx.load_cert_chain(CERTIFICATE, KEY)
  server = HTTPServerIPv6((IP, PORT), Handler)
  server.socket = ctx.wrap_socket(server.socket, server_side=True)
  logger.info('Error Page Manager listening on [%s]:%s', IP, PORT)
  server.serve_forever()


def error_page_updater_main():
  import hashlib
  import json
  import logging
  import os
  import ssl
  import subprocess
  import sys
  import time
  import urllib.request

  with open(sys.argv[1]) as f:
    config = json.load(f)

  logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
      logging.FileHandler(config['log_file']),
      logging.StreamHandler(sys.stdout),
    ],
  )
  logger = logging.getLogger('error-page-updater')

  SYNC_URL = config['sync_url']
  BASE_URL = config['base_url']
  CA_CERT = config['ca_cert_file']
  ERROR_PAGES_DIR = config['error_pages_dir']
  BUILTIN_DIR = config['builtin_dir']
  STATE_FILE = config['state_file']
  ON_UPDATE = config['on_update']
  POLL_INTERVAL = 60

  def _sha256(path):
    with open(path, 'rb') as f:
      return hashlib.sha256(f.read()).hexdigest()

  def _make_ssl_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(CA_CERT)
    return ctx

  def _get(url, ctx):
    with urllib.request.urlopen(url, context=ctx, timeout=30) as resp:
      return resp.read()

  def _load_state():
    if os.path.isfile(STATE_FILE):
      try:
        with open(STATE_FILE) as f:
          return json.load(f)
      except Exception:
        pass
    return {}

  def _save_state(state):
    with open(STATE_FILE, 'w') as f:
      json.dump(state, f)

  def _ensure_builtins():
    cluster_dir = os.path.join(ERROR_PAGES_DIR, 'cluster')
    os.makedirs(cluster_dir, exist_ok=True)
    import glob
    for src in glob.glob(os.path.join(BUILTIN_DIR, '*.html')):
      code = os.path.splitext(os.path.basename(src))[0]
      dst = os.path.join(cluster_dir, code + '.http')
      if not os.path.exists(dst):
        with open(src, encoding='utf-8') as f:
          html = f.read()
        with open(dst, 'w', encoding='utf-8') as f:
          f.write(_haproxy_format(code, html))

  def poll_once(ctx):
    try:
      manifest_data = _get(SYNC_URL, ctx)
      manifest = json.loads(manifest_data)
    except Exception as e:
      logger.warning('Could not fetch sync manifest: %s', e)
      return False

    state = _load_state()
    changed = False

    for rel_path, remote_sha in manifest.items():
      local_path = os.path.join(ERROR_PAGES_DIR, rel_path)
      local_sha = _sha256(local_path) if os.path.isfile(local_path) else None

      if local_sha == remote_sha and state.get(rel_path) == remote_sha:
        continue

      url = BASE_URL + '/' + rel_path
      try:
        data = _get(url, ctx)
      except Exception as e:
        logger.warning('Could not download %s: %s', url, e)
        continue

      os.makedirs(os.path.dirname(local_path), exist_ok=True)
      with open(local_path, 'wb') as f:
        f.write(data)
      state[rel_path] = remote_sha
      logger.info('Updated %s', rel_path)
      changed = True

    for rel_path in list(state.keys()):
      if rel_path not in manifest:
        local_path = os.path.join(ERROR_PAGES_DIR, rel_path)
        if os.path.isfile(local_path):
          os.unlink(local_path)
        del state[rel_path]
        logger.info('Removed %s (no longer in manifest)', rel_path)
        changed = True

    _save_state(state)
    return changed

  _ensure_builtins()
  ctx = _make_ssl_ctx()
  logger.info('Error Page Updater started, polling %s every %ss', SYNC_URL, POLL_INTERVAL)
  while True:
    try:
      if poll_once(ctx):
        logger.info('Pages changed, triggering haproxy reload')
        subprocess.call(ON_UPDATE, shell=True)
    except Exception as e:
      logger.error('Unexpected error in poll loop: %s', e)
    time.sleep(POLL_INTERVAL)
