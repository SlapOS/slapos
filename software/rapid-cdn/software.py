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

# One-sentence description per code, shown next to the code in the web UI.
# Mirrors the wording used in the README's "Supported error codes" table.
_EPM_CODE_DESCRIPTIONS = {
  '400': 'Frontend HAProxy could not parse the incoming HTTP request.',
  '404': 'Host header did not match any shared instance configured in this cluster.',
  '408': 'Client did not send a complete request within the cluster timeout.',
  '500': 'The CDN infrastructure itself failed to process the request.',
  '502': 'Backend was reached but the response is unparseable.',
  '503': 'No healthy backend to serve the request.',
  '504': 'Backend connection was established but did not produce a response in time.',
}


def _haproxy_format(code, html):
  reason = _EPM_HTTP_REASONS[code]
  # Leading '#'-prefixed lines are reserved for future header support.
  lines = html.split('\n')
  i = 0
  while i < len(lines) and lines[i].startswith('#'):
    i += 1
  html = '\n'.join(lines[i:])
  body = html.encode('utf-8')
  header = (
    f'HTTP/1.0 {code} {reason}\r\n'
    f'Cache-Control: no-cache\r\n'
    f'Connection: close\r\n'
    f'Content-Type: text/html; charset=utf-8\r\n'
    f'X-Content-Type-Options: nosniff\r\n'
    f'Content-Length: {len(body)}\r\n'
    f'\r\n'
  )
  return header + html


# Bound every accepted socket, TLS handshake and read/write of the error page
# manager, so a stalled or half-open client is reaped instead of permanently
# wedging the single accept loop (bug #20260722-9BC510). This mirrors kedifa's
# process-wide socket.setdefaulttimeout. Kept comfortably above a normal
# small-file request yet well below the updater's 60 s /sync poll cadence.
EPM_SOCKET_TIMEOUT = 30


def error_page_manager_main():
  import hashlib
  import http.client
  import json
  import logging
  import os
  import socket
  import ssl
  import sys
  import threading
  import urllib.parse
  from wsgiref.simple_server import make_server
  from caucase.http import ThreadingWSGIServer, CaucaseWSGIRequestHandler

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
  SHARED_TOKEN_MAP = {
    open(token_file).read().strip(): shared_reference
    for shared_reference, token_file in config['shared_token_files']
  }

  SUPPORTED_CODES = ['400', '404', '408', '500', '502', '503', '504']
  SHARED_CODES = ['502', '503', '504']

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
      haproxy_dir = os.path.join(ERROR_PAGES_DIR, 'haproxy', 'shared', slot)
    os.makedirs(haproxy_dir, exist_ok=True)
    haproxy_path = os.path.join(haproxy_dir, f'{code}.http')

    if slot == 'cluster':
      html = _read_html(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'))
    else:
      html = _read_html(os.path.join(ERROR_PAGES_DIR, 'shared', slot, f'{code}.html'))
      if html is None:
        html = _read_html(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'))

    if html is None:
      html = _read_html(os.path.join(BUILTIN_DIR, f'{code}.html'))

    with open(haproxy_path, 'w', encoding='utf-8') as f:
      f.write(_haproxy_format(code, html))

  def _refresh_all_for_code(code):
    _refresh_haproxy_file('cluster', code)
    shared_dir = os.path.join(ERROR_PAGES_DIR, 'haproxy', 'shared')
    if os.path.isdir(shared_dir):
      for ref in os.listdir(shared_dir):
        if code in SHARED_CODES:
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

  def _render_web_ui(codes, source_dir):
    rows = ''
    for code in codes:
      source_file = os.path.join(source_dir, f'{code}.html')
      html = (_read_html(source_file) or '').replace(
        '&', '&amp;').replace('<', '&lt;')
      reason = _EPM_HTTP_REASONS[code]
      desc = _EPM_CODE_DESCRIPTIONS[code]
      rows += f'''
        <tr>
          <td class="code">
            <div class="code-num">{code}</div>
            <div class="code-reason">{reason}</div>
            <div class="code-desc">{desc}</div>
          </td>
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
             box-shadow: 0 1px 4px rgba(0,0,0,.08); border-radius: 6px; overflow: hidden;
             table-layout: fixed; }}
    th, td {{ padding: .75rem 1rem; text-align: left; border-bottom: 1px solid #eef0f3;
              vertical-align: top; }}
    th {{ background: #f0f2f5; font-size: .85rem; color: #555; }}
    th.code-col, td.code {{ width: 22%; min-width: 14rem; }}
    th.actions-col, td.actions {{ width: 8rem; }}
    td.code .code-num {{ font-weight: 700; font-size: 1.4rem; color: #333;
                         line-height: 1; }}
    td.code .code-reason {{ font-weight: 600; color: #555; margin-top: .35rem; }}
    td.code .code-desc {{ font-size: 0.8rem; color: #888; margin-top: .35rem;
                          line-height: 1.4; font-weight: normal; }}
    textarea {{ width: 100%; min-height: 6rem; font-family: monospace;
                font-size: .85rem; border: 1px solid #dde; border-radius: 4px;
                padding: .4rem; resize: both; }}
    button {{ padding: .3rem .8rem; border: none; border-radius: 4px;
              cursor: pointer; margin: .15rem 0; }}
    button[value^="save"] {{ background: #4a90d9; color: #fff; }}
    button[value^="reset"] {{ background: #e0e4ea; color: #333; }}
  </style>
</head>
<body>
  <h1>Error Page Manager</h1>
  <form method="post">
    <table>
      <thead><tr>
        <th class="code-col">Code</th>
        <th>HTML Content</th>
        <th class="actions-col">Actions</th>
      </tr></thead>
      <tbody>{rows}
      </tbody>
    </table>
  </form>
</body>
</html>'''

  def _operator_web_ui():
    return _render_web_ui(
      SUPPORTED_CODES,
      os.path.join(ERROR_PAGES_DIR, 'operator'))

  def _shared_web_ui(ref):
    return _render_web_ui(
      SHARED_CODES,
      os.path.join(ERROR_PAGES_DIR, 'shared', ref))

  # The manager is served as a WSGI application by caucase's threading server
  # (the same model kedifa uses), so a single stalled or half-open client can
  # no longer wedge the whole service -- see bug #20260722-9BC510. Every
  # request runs in its own daemon thread; a process-wide socket timeout
  # (EPM_SOCKET_TIMEOUT) bounds the TLS handshake and each read/write; and
  # wsgiref keeps connections short-lived (no HTTP/1.1 keep-alive).
  def _parse_path(path):
    parts = path.lstrip('/').split('/', 2)
    section = parts[0] if parts else ''
    token = parts[1] if len(parts) > 1 else ''
    rest = parts[2] if len(parts) > 2 else ''
    return section, token, rest

  def application(environ, start_response):
    method = environ['REQUEST_METHOD']
    path = environ.get('PATH_INFO', '') or ''
    section, token, rest = _parse_path(path)

    def send(code, body, content_type='text/plain'):
      if isinstance(body, str):
        body = body.encode()
      start_response(
        '%d %s' % (code, http.client.responses.get(code, 'Unknown')),
        [
          ('Content-Type', content_type),
          ('Content-Length', str(len(body))),
        ])
      return [body]

    def send_json(data, code=200):
      return send(code, json.dumps(data), 'application/json')

    def read_body():
      try:
        length = int(environ.get('CONTENT_LENGTH') or 0)
      except (TypeError, ValueError):
        length = 0
      if length > 2 * 1024 * 1024:  # 2 MB limit
        return None
      data = environ['wsgi.input'].read(length) if length > 0 else b''
      return data.decode('utf-8', errors='replace')

    if method == 'GET':
      if section == 'sync':
        if token != READ_TOKEN:
          return send(401, 'Unauthorized')
        with _lock:
          return send_json(_build_manifest())
      elif section == 'haproxy':
        if token != READ_TOKEN:
          return send(401, 'Unauthorized')
        full = os.path.normpath(
          os.path.join(ERROR_PAGES_DIR, 'haproxy', rest))
        if not full.startswith(ERROR_PAGES_DIR + os.sep + 'haproxy' + os.sep):
          return send(403, 'Forbidden')
        if not os.path.isfile(full):
          return send(404, 'Not found')
        with open(full, 'rb') as f:
          return send(200, f.read(), 'application/octet-stream')
      elif section == 'operator':
        if token != OPERATOR_TOKEN:
          return send(401, 'Unauthorized')
        if not rest:
          return send(200, _operator_web_ui(), 'text/html')
        elif rest in SUPPORTED_CODES:
          op_file = os.path.join(ERROR_PAGES_DIR, 'operator', f'{rest}.html')
          return send(200, _read_html(op_file) or '', 'text/html')
        else:
          return send(404, 'Unknown code')
      elif section == 'shared':
        ref = SHARED_TOKEN_MAP.get(token)
        if ref is None:
          return send(401, 'Unauthorized')
        if not rest:
          return send(200, _shared_web_ui(ref), 'text/html')
        elif rest in SHARED_CODES:
          shared_file = os.path.join(
            ERROR_PAGES_DIR, 'shared', ref, f'{rest}.html')
          return send(200, _read_html(shared_file) or '', 'text/html')
        else:
          return send(404, 'Unknown code')
      else:
        return send(404, 'Not found')

    elif method == 'POST':
      if section == 'operator' and token == OPERATOR_TOKEN:
        valid_codes = SUPPORTED_CODES
        source_dir = os.path.join(ERROR_PAGES_DIR, 'operator')
        def _refresh(code):
          _refresh_all_for_code(code)
      elif section == 'shared' and SHARED_TOKEN_MAP.get(token) is not None:
        ref = SHARED_TOKEN_MAP[token]
        valid_codes = SHARED_CODES
        source_dir = os.path.join(ERROR_PAGES_DIR, 'shared', ref)
        def _refresh(code):
          _refresh_haproxy_file(ref, code)
      else:
        return send(401, 'Unauthorized')
      body = read_body()
      if body is None:
        return send(413, 'Too large')
      params = urllib.parse.parse_qs(body, keep_blank_values=True)
      action = params.get('action', [''])[0]
      if action.startswith('save_'):
        code = action[5:]
        if code not in valid_codes:
          return send(400, 'Unknown code')
        html = params.get(f'html_{code}', [''])[0]
        with _lock:
          os.makedirs(source_dir, exist_ok=True)
          with open(os.path.join(source_dir, f'{code}.html'), 'w') as f:
            f.write(html)
          _refresh(code)
      elif action.startswith('reset_'):
        code = action[6:]
        if code not in valid_codes:
          return send(400, 'Unknown code')
        with _lock:
          source_file = os.path.join(source_dir, f'{code}.html')
          if os.path.exists(source_file):
            os.unlink(source_file)
          _refresh(code)
      # Browsers expect POST-redirect-GET; the meta refresh achieves the
      # same UX (the form is shown again after submission) while keeping a
      # plain 200 response that integrates cleanly with non-browser HTTP
      # clients (curl-based test runners stumble on 3xx + TLS close).
      target = path.rsplit('/', 1)[0] + '/'
      return send(
        200,
        b'<!DOCTYPE html><html><head>'
        b'<meta http-equiv="refresh" content="0; url=' + target.encode() +
        b'"></head><body>Done.</body></html>',
        'text/html; charset=utf-8')

    elif method == 'PUT':
      if section == 'operator':
        if token != OPERATOR_TOKEN:
          return send(401, 'Unauthorized')
        code = rest
        if code not in SUPPORTED_CODES:
          return send(400, 'Unknown code')
        html = read_body()
        if html is None:
          return send(413, 'Too large')
        with _lock:
          os.makedirs(os.path.join(ERROR_PAGES_DIR, 'operator'), exist_ok=True)
          with open(os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html'), 'w') as f:
            f.write(html)
          _refresh_all_for_code(code)
        return send(204, '')
      elif section == 'shared':
        ref = SHARED_TOKEN_MAP.get(token)
        if ref is None:
          return send(401, 'Unauthorized')
        code = rest
        if code not in SHARED_CODES:
          return send(
            400,
            f'Shared instances may only set: {", ".join(SHARED_CODES)}')
        html = read_body()
        if html is None:
          return send(413, 'Too large')
        with _lock:
          shared_dir = os.path.join(ERROR_PAGES_DIR, 'shared', ref)
          os.makedirs(shared_dir, exist_ok=True)
          with open(os.path.join(shared_dir, f'{code}.html'), 'w') as f:
            f.write(html)
          _refresh_haproxy_file(ref, code)
        return send(204, '')
      else:
        return send(404, 'Not found')

    elif method == 'DELETE':
      if section == 'operator':
        if token != OPERATOR_TOKEN:
          return send(401, 'Unauthorized')
        code = rest
        if code not in SUPPORTED_CODES:
          return send(400, 'Unknown code')
        with _lock:
          op_file = os.path.join(ERROR_PAGES_DIR, 'operator', f'{code}.html')
          if os.path.exists(op_file):
            os.unlink(op_file)
          _refresh_all_for_code(code)
        return send(204, '')
      elif section == 'shared':
        ref = SHARED_TOKEN_MAP.get(token)
        if ref is None:
          return send(401, 'Unauthorized')
        code = rest
        if code not in SHARED_CODES:
          return send(
            400,
            f'Shared instances may only set: {", ".join(SHARED_CODES)}')
        with _lock:
          shared_file = os.path.join(
            ERROR_PAGES_DIR, 'shared', ref, f'{code}.html')
          if os.path.exists(shared_file):
            os.unlink(shared_file)
          _refresh_haproxy_file(ref, code)
        return send(204, '')
      else:
        return send(404, 'Not found')

    else:
      return send(404, 'Not found')

  with _lock:
    for code in SUPPORTED_CODES:
      _refresh_haproxy_file('cluster', code)
    for ref in set(SHARED_TOKEN_MAP.values()):
      for code in SHARED_CODES:
        _refresh_haproxy_file(ref, code)
  logger.info('Initialized haproxy error files')

  ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  ctx.load_cert_chain(CERTIFICATE, KEY)

  # Time-bound accepted sockets / TLS handshake / read-write before building
  # the server, then wrap the listening socket and bind/activate exactly as
  # kedifa does (kedifa/app.py) -- ThreadingWSGIServer is created with
  # bind_and_activate=False so the socket can be TLS-wrapped first.
  socket.setdefaulttimeout(EPM_SOCKET_TIMEOUT)
  httpd = make_server(
    IP, PORT, application, ThreadingWSGIServer, CaucaseWSGIRequestHandler)
  httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
  httpd.server_bind()
  httpd.server_activate()
  logger.info('Error Page Manager listening on [%s]:%s', IP, PORT)
  httpd.serve_forever()


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
