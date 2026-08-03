#!/usr/bin/env python3
"""End-to-end test harness for MR 2159 (rapid-cdn error-page-manager).

Runs the scenarios documented in ``epm-e2e-procedure.md`` against a live
rapid-cdn cluster deployed on this node, and writes a dated Markdown report
mirroring the procedure's scenario list.

It is deliberately stdlib-only (no ``requests``/``slapos`` import): the live
endpoints and on-disk paths come from ``epm-params.json`` produced by
``epm-collect-params.py`` (run via ``slapos console``).

Usage:
    python3 test/epm-e2e.py --params test/epm-params.json \\
        --phase {baseline,full} --report test/epm-e2e-report-DATE.md

Phases:
    baseline  M1, M9, M8   (pre-fix SR: demonstrates the wedge / O(shared))
    full      M1..M12      (fixed SR: everything, slow polling scenarios last)
"""
import argparse
import datetime
import http.client
import json
import os
import socket
import ssl
import tempfile
import threading
import time
import urllib.parse

SUPPORTED_CODES = ['400', '404', '408', '500', '502', '503', '504']
SHARED_CODES = ['502', '503', '504']
POLL_TIMEOUT = 150          # updater POLL_INTERVAL is 60s; allow >2 cycles
EPM_SOCKET_TIMEOUT = 30     # matches software.EPM_SOCKET_TIMEOUT


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
class Ctx:
  """Holds shared state (params, ssl contexts) for the scenarios."""

  def __init__(self, params):
    self.p = params
    self.epm = params['epm']
    self.frontend = params.get('frontend') or {}
    # Verify the EPM self-signed cert via cafile, but skip hostname match
    # (SAN is an IP literal; we relax it exactly like the CI harness's
    # verify=<cert-file>).
    cert_file = tempfile.NamedTemporaryFile(
        suffix='.crt', delete=False, mode='w')
    cert_file.write(self.epm['certificate'])
    cert_file.close()
    self.cert_path = cert_file.name
    self.verify_ctx = ssl.create_default_context(cafile=self.cert_path)
    self.verify_ctx.check_hostname = False

  def close(self):
    if os.path.exists(self.cert_path):
      os.unlink(self.cert_path)

  # -- EPM (manager) requests, cert-verified ------------------------------- #
  def epm_request(self, method, url, body=None, timeout=30):
    u = urllib.parse.urlparse(url)
    path = u.path + (('?' + u.query) if u.query else '')
    conn = http.client.HTTPSConnection(
        u.hostname, u.port, timeout=timeout, context=self.verify_ctx)
    try:
      conn.request(method, path, body=body)
      resp = conn.getresponse()
      data = resp.read()
      return resp.status, data.decode('utf-8', 'replace')
    finally:
      conn.close()

  def get(self, url, timeout=30):
    return self.epm_request('GET', url, timeout=timeout)

  def put(self, url, body, timeout=30):
    return self.epm_request('PUT', url, body=body.encode('utf-8'),
                            timeout=timeout)

  def delete(self, url, timeout=30):
    return self.epm_request('DELETE', url, timeout=timeout)

  def manifest(self, timeout=30):
    status, text = self.get(self.epm['sync_url'], timeout=timeout)
    if status != 200:
      raise RuntimeError('sync returned %s' % status)
    return json.loads(text)

  def wait_ready(self, timeout=90):
    begin = time.time()
    while time.time() - begin < timeout:
      try:
        if self.get(self.epm['sync_url'], timeout=5)[0] == 200:
          return True
      except Exception:
        pass
      time.sleep(2)
    return False

  # -- Frontend serving requests, SNI + Host to an IP, unverified ---------- #
  def frontend_get(self, domain, path='/', timeout=20):
    ip = self.frontend['https_ip']
    port = self.frontend['https_port']
    uctx = ssl._create_unverified_context()
    raw = socket.create_connection((ip, port), timeout=timeout)
    try:
      s = uctx.wrap_socket(raw, server_hostname=domain)
      req = ('GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n'
             % (path, domain))
      s.sendall(req.encode())
      buf = b''
      while True:
        try:
          chunk = s.recv(65536)
        except socket.timeout:
          break
        if not chunk:
          break
        buf += chunk
      s.close()
    finally:
      raw.close()
    text = buf.decode('utf-8', 'replace')
    status = None
    first = text.split('\r\n', 1)[0].split()
    if len(first) >= 2 and first[1].isdigit():
      status = int(first[1])
    return status, text

  # -- Raw stalled TLS connection (mirrors _open_stalled_connection) ------- #
  def open_stalled(self):
    host, port = self.epm['host'], self.epm['port']
    cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cctx.check_hostname = False
    cctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection((host, port), timeout=6)
    # wrap_socket detaches raw's fd into tls; operate on tls only afterward.
    tls = cctx.wrap_socket(raw, server_hostname=None)
    tls.sendall(b'GET /sync/')          # no terminating CRLF: never completes
    tls.settimeout(None)                # then hold it open indefinitely
    return tls


def poll_until(predicate, timeout=POLL_TIMEOUT, interval=5):
  """Return (True, elapsed) as soon as predicate() is truthy, else (False, t)."""
  begin = time.time()
  while time.time() - begin < timeout:
    try:
      if predicate():
        return True, time.time() - begin
    except Exception:
      pass
    time.sleep(interval)
  return False, time.time() - begin


# --------------------------------------------------------------------------- #
# Scenarios.  Each returns a dict with the report fields.
# --------------------------------------------------------------------------- #
def _result(mid, title, basis, expected, observed, passed):
  return {'id': mid, 'title': title, 'basis': basis,
          'expected': expected, 'observed': observed, 'passed': passed}


def m1_manifest_no_shared(c):
  m = c.manifest()
  missing = [code for code in SUPPORTED_CODES
             if 'cluster/%s.http' % code not in m]
  shared = sorted(k for k in m if k.startswith('shared/'))
  passed = (not missing) and (not shared)
  observed = ('cluster keys: %d/7 present%s; shared keys: %d %s'
              % (7 - len(missing),
                 ('' if not missing else ' (missing %s)' % missing),
                 len(shared),
                 (shared[:6] + (['...'] if len(shared) > 6 else []))))
  return _result(
      'M1', 'Manifest lists cluster defaults + zero shared overrides',
      'test_sync_manifest_lists_cluster_files_and_only_real_overrides',
      '7 cluster/*.http keys and 0 shared/* keys (no overrides set)',
      observed, passed)


def m2_manifest_override(c):
  ref, info = next(iter(c.epm['shared'].items()))
  up = info['upload_url']
  key = 'shared/%s/503.http' % ref
  steps = []
  try:
    st, _ = c.put(up + '503', '<html>o</html>')
    steps.append('PUT 503 -> %s' % st)
    shared = sorted(k for k in c.manifest() if k.startswith('shared/'))
    steps.append('manifest shared after PUT: %s' % shared)
    only_one = (shared == [key])
    st, _ = c.delete(up + '503')
    steps.append('DELETE 503 -> %s' % st)
    shared_after = sorted(k for k in c.manifest() if k.startswith('shared/'))
    steps.append('manifest shared after DELETE: %s' % shared_after)
    passed = only_one and (key not in shared_after)
  finally:
    c.delete(up + '503')
  return _result(
      'M2', 'Slave override adds exactly one manifest key; delete removes it',
      'test_sync_manifest_lists_cluster_files_and_only_real_overrides',
      'after PUT: shared == [%s]; after DELETE: key absent' % key,
      '; '.join(steps), passed)


def m3_seed_symlinks(c):
  epd = c.frontend.get('error_pages_dir')
  if not epd or not os.path.isdir(epd):
    return _result('M3', 'Seed created cluster files + fallback symlinks',
                   'test_seed_creates_cluster_files_and_fallback_symlinks',
                   'per-slave SHARED-code files are symlinks to cluster page',
                   'frontend error_pages_dir not found', None)
  problems = []
  for code in SUPPORTED_CODES:
    p = os.path.join(epd, 'cluster', '%s.http' % code)
    if not (os.path.isfile(p) and not os.path.islink(p)):
      problems.append('cluster/%s.http not a real file' % code)
  n_links = 0
  for s in c.frontend['slaves']:
    ref = s['ref']
    for code in SHARED_CODES:
      link = os.path.join(epd, 'shared', ref, '%s.http' % code)
      if os.path.islink(link):
        target = os.readlink(link)
        if target != os.path.join('..', '..', 'cluster', '%s.http' % code):
          problems.append('%s -> %s (unexpected target)' % (link, target))
        elif not os.path.isfile(link):
          problems.append('%s symlink dangling' % link)
        else:
          n_links += 1
      else:
        problems.append('shared/%s/%s.http not a symlink' % (ref, code))
    # cluster-only code must not be materialised per-slave
    if os.path.exists(os.path.join(epd, 'shared', ref, '404.http')):
      problems.append('shared/%s/404.http should not exist' % ref)
  passed = not problems
  observed = ('%d fallback symlinks verified across %d slaves%s'
              % (n_links, len(c.frontend['slaves']),
                 '' if passed else '; problems: ' + '; '.join(problems[:8])))
  return _result(
      'M3', 'Seed created cluster files + per-slave fallback symlinks',
      'test_seed_creates_cluster_files_and_fallback_symlinks',
      'cluster/*.http real files; shared/<ref>/<502,503,504>.http symlinks '
      'to ../../cluster/<code>.http; no per-slave file for cluster-only codes',
      observed, passed)


def m4_frontend_serves_cluster_fallback(c):
  if not c.frontend.get('slaves'):
    return _result('M4', 'Backends down + no override -> cluster 503 served',
                   'seed purpose / backend-haproxy validates',
                   'each slave frontend returns 503 builtin/cluster page',
                   'no frontend slaves', None)
  details = []
  ok = True
  for s in c.frontend['slaves']:
    status, text = c.frontend_get(s['domain'])
    served = ('Service Unavailable' in text) or ('503' in (text[:40]))
    details.append('%s -> HTTP %s, cluster-page=%s' % (
        s['domain'], status, served))
    if not (status == 503 and served):
      ok = False
  return _result(
      'M4', 'All backends down, no override -> frontend serves cluster 503',
      'seed purpose (backend-haproxy validates against fallback symlinks)',
      'every slave returns HTTP 503 with the builtin/cluster page',
      '; '.join(details), ok)


def m5_new_slave_inherits_cluster(c):
  ref = next(iter(c.epm['shared']))
  op = c.epm['operator_url']
  base = c.epm['base_url']
  op_html = '<html><body>Operator 503 inherit %d</body></html>' % os.getpid()
  steps = []
  try:
    st, _ = c.put(op + '503', op_html)
    steps.append('operator PUT 503 -> %s' % st)
    st, _ = c.get('%s/shared/%s/503.http' % (base, ref))
    steps.append('manager shared/%s/503.http -> %s' % (ref, st))
    no_perslave = (st == 404)
    st_c, cl = c.get('%s/cluster/503.http' % base)
    steps.append('cluster/503.http carries operator html: %s'
                 % (op_html in cl))
    passed = no_perslave and (op_html in cl)
  finally:
    c.delete(op + '503')
  return _result(
      'M5', 'Slave without override serves cluster page (no per-slave file)',
      'test_new_slave_uses_cluster_page_until_it_overrides',
      'manager has no shared/<ref>/503.http (404); cluster carries operator page',
      '; '.join(steps), passed)


def _lifecycle_override(c):
  """Shared driver for M6/M7: PUT then DELETE, watching the frontend file."""
  ref = c.frontend['slaves'][0]['ref']
  domain = c.frontend['slaves'][0]['domain']
  up = c.epm['shared'][ref]['upload_url']
  epd = c.frontend['error_pages_dir']
  fpath = os.path.join(epd, 'shared', ref, '503.http')
  marker = 'E2E MR2159 slave 503 %d' % os.getpid()
  html = '<html><body>%s</body></html>' % marker

  m6_steps = []
  st, _ = c.put(up + '503', html)
  m6_steps.append('slave PUT 503 -> %s' % st)
  real_file = os.path.isfile(fpath) and not os.path.islink(fpath)
  got, t = poll_until(
      lambda: os.path.isfile(fpath) and not os.path.islink(fpath)
      and marker in open(fpath).read())
  m6_steps.append('frontend real-file with override after %.0fs: %s' % (t, got))
  served, ts = poll_until(lambda: marker in c.frontend_get(domain)[1])
  m6_steps.append('frontend serves override after %.0fs: %s' % (ts, served))
  m6 = _result(
      'M6', 'Override replaces fallback symlink with a real file (served)',
      'updater override path (islink -> real file)',
      'frontend shared/<ref>/503.http becomes a real file with the override '
      'and is served', '; '.join(m6_steps), got and served)

  m7_steps = []
  st, _ = c.delete(up + '503')
  m7_steps.append('slave DELETE 503 -> %s' % st)
  reverted, t = poll_until(lambda: os.path.islink(fpath))
  m7_steps.append('frontend file reverted to symlink after %.0fs: %s'
                  % (t, reverted))
  target_ok = (os.path.islink(fpath)
               and os.readlink(fpath) == os.path.join('..', '..', 'cluster',
                                                       '503.http'))
  m7_steps.append('symlink target correct: %s' % target_ok)
  cluster_served, ts = poll_until(
      lambda: marker not in c.frontend_get(domain)[1]
      and c.frontend_get(domain)[0] == 503)
  m7_steps.append('frontend serves cluster page again after %.0fs: %s'
                  % (ts, cluster_served))
  m7 = _result(
      'M7', 'Reset restores fallback symlink (not delete); cluster served',
      '_restore_fallback_symlink',
      'frontend file is a symlink to ../../cluster/503.http again; override '
      'no longer served', '; '.join(m7_steps),
      reverted and target_ok and cluster_served)
  return m6, m7


def m8_stalled_client(c, phase):
  stalled = []
  open_errors = 0
  try:
    for _ in range(10):                    # > old listen backlog of 5
      try:
        stalled.append(c.open_stalled())
      except Exception:
        open_errors += 1                   # backlog already full / wedged
    ok = 0
    begin = time.time()
    last_err = None
    while time.time() - begin < 30:
      try:
        status, _ = c.get(c.epm['sync_url'], timeout=10)
        if status == 200:
          ok += 1
          if ok >= 5:
            break
      except Exception as e:
        last_err = repr(e)
        break
    passed = ok >= 5
    observed = ('%d/5 successful /sync probes while %d clients stalled '
                '(%d stalled-conn open errors)%s'
                % (ok, len(stalled), open_errors,
                   '' if not last_err else '; last probe error: ' + last_err))
  finally:
    for tls in stalled:
      try:
        tls.close()
      except Exception:
        pass
  return _result(
      'M8', 'Stalled clients do not wedge the manager',
      'test_stalled_client_does_not_wedge_manager',
      '/sync answers 200 at least 5 times within 30s despite 10 stalled '
      'connections', observed, passed)


def m9_concurrent(c):
  WORKERS, DURATION = 20, 10
  stop = threading.Event()
  counters = {'ok': 0, 'err': 0}
  lock = threading.Lock()

  def worker():
    while not stop.is_set():
      try:
        status, _ = c.get(c.epm['sync_url'], timeout=30)
        with lock:
          counters['ok' if status == 200 else 'err'] += 1
      except Exception:
        with lock:
          counters['err'] += 1

  threads = [threading.Thread(target=worker, daemon=True)
             for _ in range(WORKERS)]
  for t in threads:
    t.start()
  time.sleep(DURATION)
  stop.set()
  for t in threads:
    t.join(timeout=60)
  passed = counters['ok'] > 0 and counters['err'] == 0
  observed = 'ok=%d err=%d over %ds with %d workers' % (
      counters['ok'], counters['err'], DURATION, WORKERS)
  return _result(
      'M9', 'Concurrent /sync clients all served without error',
      'test_concurrent_sync_requests',
      'all requests return 200, zero errors', observed, passed)


def m10_timeout_reaping(c):
  tls = c.open_stalled()
  begin = time.time()
  closed_after = None
  try:
    tls.settimeout(EPM_SOCKET_TIMEOUT + 20)
    while time.time() - begin < EPM_SOCKET_TIMEOUT + 15:
      try:
        chunk = tls.recv(4096)
      except (ssl.SSLError, socket.timeout, OSError):
        closed_after = time.time() - begin
        break
      if chunk == b'':
        closed_after = time.time() - begin
        break
  finally:
    try:
      tls.close()
    except Exception:
      pass
  if closed_after is None:
    return _result('M10', 'Stalled connection reaped by socket timeout',
                   'EPM_SOCKET_TIMEOUT server reaping',
                   'server closes the idle connection within ~%ds'
                   % EPM_SOCKET_TIMEOUT,
                   'connection still open after %ds' % (EPM_SOCKET_TIMEOUT + 15),
                   None)
  passed = closed_after <= EPM_SOCKET_TIMEOUT + 10
  return _result(
      'M10', 'Stalled connection reaped by socket timeout',
      'EPM_SOCKET_TIMEOUT server reaping',
      'server closes the idle connection within ~%ds' % EPM_SOCKET_TIMEOUT,
      'connection closed after %.0fs' % closed_after, passed)


def m11_operator_change_not_per_slave(c):
  ref = next(iter(c.epm['shared']))
  op, base = c.epm['operator_url'], c.epm['base_url']
  html = '<html><body>Operator 502 M11 %d</body></html>' % os.getpid()
  steps = []
  try:
    st, _ = c.put(op + '502', html)
    steps.append('operator PUT 502 -> %s' % st)
    st_c, cl = c.get('%s/cluster/502.http' % base)
    steps.append('cluster/502.http carries operator html: %s' % (html in cl))
    st_s, _ = c.get('%s/shared/%s/502.http' % (base, ref))
    steps.append('manager shared/%s/502.http -> %s' % (ref, st_s))
    passed = (html in cl) and (st_s == 404)
  finally:
    c.delete(op + '502')
  return _result(
      'M11', 'Operator page updates cluster file, not any per-slave file',
      'test_operator_change_updates_cluster_file_not_per_slave',
      'cluster/502.http carries the page; manager shared/<ref>/502.http is 404',
      '; '.join(steps), passed)


def _load_installed_fn(func_name):
  """Extract and exec just one top-level function from the software.py installed
  in the compiled SR. The EPM helpers are self-contained (os/shutil imported
  internally), so we exec only the function source -- importing the whole module
  would pull in the SR-only 'caucase' egg absent from the system python."""
  import glob
  import ast
  for path in glob.glob('/opt/slapgrid/*/parts/software-prepare/software.py'):
    try:
      src = open(path).read()
    except OSError:
      continue
    if ('def %s' % func_name) not in src:
      continue
    for node in ast.parse(src).body:
      if isinstance(node, ast.FunctionDef) and node.name == func_name:
        ns = {}
        exec(ast.get_source_segment(src, node), ns)
        return ns[func_name], path
  return None, None


def m13_prune(c):
  """Removed-slave pruning: the installed _prune_removed_shared_overrides drops
  the per-slave override dirs (both shared/ and haproxy/shared/) of refs no
  longer in the shared list, and keeps active refs (mirrors TestErrorPagePrune).
  The shared list is retention-resolved upstream by the SlapOS master, so no
  EPM-side retention parameter exists anymore."""
  import tempfile
  import shutil
  steps = []

  prune, path = _load_installed_fn('_prune_removed_shared_overrides')
  if prune is None:
    return _result('M13', 'Removed-slave overrides pruned, active kept',
                   'TestErrorPagePrune',
                   'active ref kept, removed ref pruned in both trees',
                   'installed _prune_removed_shared_overrides not found', False)
  steps.append('prune fn from: %s' % path)

  def dirs(base, ref):
    return (os.path.join(base, 'shared', ref),
            os.path.join(base, 'haproxy', 'shared', ref))

  t = tempfile.mkdtemp()
  try:
    for ref in ('a', 'b'):
      for d in dirs(t, ref):
        os.makedirs(d)
        open(os.path.join(d, '503.http'), 'w').close()
    prune(t, {'a'})
    a_src, a_hap = dirs(t, 'a')
    b_src, b_hap = dirs(t, 'b')
    kept = os.path.isdir(a_src) and os.path.isdir(a_hap)
    pruned = (not os.path.isdir(b_src)) and (not os.path.isdir(b_hap))
    steps.append('active "a" kept (shared+haproxy): %s' % kept)
    steps.append('removed "b" pruned (shared+haproxy): %s' % pruned)
    # sanity: pruning is confined to per-slave dirs (cluster tree untouched)
    passed = kept and pruned
  finally:
    shutil.rmtree(t)
  return _result(
      'M13', 'Removed-slave overrides pruned, active kept',
      'TestErrorPagePrune',
      'ref in active set keeps shared/<ref> and haproxy/shared/<ref>; ref '
      'absent from the set has both removed',
      '; '.join(steps), passed)


def m12_operator_delete_reverts(c):
  base, op = c.epm['base_url'], c.epm['operator_url']
  ref = next(iter(c.epm['shared']))
  html = '<html><body>Operator 503 M12 %d</body></html>' % os.getpid()
  steps = []
  c.put(op + '503', html)
  _, cl = c.get('%s/cluster/503.http' % base)
  steps.append('after PUT cluster has op html: %s' % (html in cl))
  st_s, _ = c.get('%s/shared/%s/503.http' % (base, ref))
  steps.append('shared 404 while op set: %s' % (st_s == 404))
  c.delete(op + '503')
  _, cl2 = c.get('%s/cluster/503.http' % base)
  reverted = cl2.startswith('HTTP/1.0 503 ') and (html not in cl2)
  steps.append('after DELETE cluster reverted to builtin: %s' % reverted)
  st_s2, _ = c.get('%s/shared/%s/503.http' % (base, ref))
  steps.append('shared still 404 after delete: %s' % (st_s2 == 404))
  passed = (html in cl) and (st_s == 404) and reverted and (st_s2 == 404)
  return _result(
      'M12', 'Operator delete reverts cluster to builtin; shared stays absent',
      'test_operator_delete_reverts_cluster_file_to_builtin',
      'cluster/503.http back to "HTTP/1.0 503 " builtin; shared 404 throughout',
      '; '.join(steps), passed)


def m14_slave_override_precedence(c):
  """Exhaustive slave-override precedence at the manager, for EVERY slave-
  overridable code (SHARED_CODES = 502/503/504):
    - operator sets <code> and the slave sets <code>: the slave override wins in
      its own per-slave file, while the operator page stays on the cluster file;
    - delete the slave override -> per-slave file 404 (frontend falls back to the
      cluster = operator page); delete the operator override -> cluster reverts to
      the builtin page.
  Plus the negative case: a slave may NOT override cluster-only codes
  (400/404/408/500) -> PUT is rejected 400, DELETE rejected 400.
  Mirrors CI test_slave_override_takes_precedence_over_operator / full_cascade,
  extended to all three shared codes."""
  ref = next(iter(c.epm['shared']))
  up = c.epm['shared'][ref]['upload_url']
  op = c.epm['operator_url']
  base = c.epm['base_url']
  steps = []
  passed = True
  pid = os.getpid()
  try:
    for code in SHARED_CODES:                       # 502, 503, 504
      ophtml = '<html><body>OPERATOR %s %d</body></html>' % (code, pid)
      slhtml = '<html><body>SLAVE %s %d</body></html>' % (code, pid)
      so, _ = c.put(op + code, ophtml)
      ss, _ = c.put(up + code, slhtml)
      # slave override wins in its own file (slave content, not operator)
      st, per = c.get('%s/shared/%s/%s.http' % (base, ref, code))
      slave_wins = (st == 200 and slhtml in per and ophtml not in per
                    and per.startswith('HTTP/1.0 %s ' % code))
      # operator page is on the cluster file
      _, cl = c.get('%s/cluster/%s.http' % (base, code))
      op_on_cluster = ophtml in cl
      # remove slave override -> per-slave file gone (falls back to cluster)
      c.delete(up + code)
      st2, _ = c.get('%s/shared/%s/%s.http' % (base, ref, code))
      reverted = (st2 == 404)
      # remove operator override -> cluster back to builtin
      c.delete(op + code)
      _, cl2 = c.get('%s/cluster/%s.http' % (base, code))
      builtin = cl2.startswith('HTTP/1.0 %s ' % code) and ophtml not in cl2
      code_ok = slave_wins and op_on_cluster and reverted and builtin
      steps.append('%s: put(op=%s,sl=%s) slave_wins=%s op_on_cluster=%s '
                   'del_slave->404=%s del_op->builtin=%s'
                   % (code, so, ss, slave_wins, op_on_cluster, reverted, builtin))
      passed = passed and code_ok
    # negative: slave cannot set cluster-only codes
    forb = []
    for code in [x for x in SUPPORTED_CODES if x not in SHARED_CODES]:
      putc, _ = c.put(up + code, '<html>x</html>')
      delc, _ = c.delete(up + code)
      forb.append('%s:PUT=%s,DEL=%s' % (code, putc, delc))
      if putc != 400 or delc != 400:
        passed = False
    steps.append('cluster-only codes rejected (want 400/400): %s' % ' '.join(forb))
  finally:
    # best-effort cleanup of anything left set
    for code in SHARED_CODES:
      c.delete(up + code)
      c.delete(op + code)
  return _result(
      'M14', 'Slave override precedence over operator, all slave codes',
      'test_slave_override_takes_precedence_over_operator / test_full_cascade',
      'for each of 502/503/504 the slave override wins in shared/<ref>/<code>.http '
      'while operator stays on cluster; delete cascades slave->cluster->builtin; '
      '400/404/408/500 slave PUT/DELETE rejected 400',
      '; '.join(steps), passed)


def m15_urlless_slave_has_no_master_override(c):
  """A urlless (parameterless) slave has NO master override -- accepted by design.

  Materialising a per-slave override for every slave (the "fix" for the mixed-SR
  symptom) was found to be an unusual corner case with bad impact, so the
  decision is: a slave that supplies no url / sets no override of its own gets
  NO per-slave override from the master (operator/cluster). It has no per-slave
  file and no manifest entry, and an operator (cluster) page does NOT get pushed
  down to it as a per-slave override. (Where a frontend has the seed fallback
  symlink it still serves the cluster page; a urlless slave has no backend to
  serve anyway.)"""
  import json
  refs = list(c.epm['shared'].keys())
  empty = next((r for r in refs if 'empty' in r), refs[-1])
  up = c.epm['shared'][empty]['upload_url']
  op = c.epm['operator_url']
  base = c.epm['base_url']
  steps = ['urlless ref: %s' % empty]
  try:
    for code in SHARED_CODES:              # ensure no own override
      c.delete(up + code)
    # no per-slave override file for any shared code
    per = {code: c.get('%s/shared/%s/%s.http' % (base, empty, code))[0]
           for code in SHARED_CODES}
    no_file = all(v == 404 for v in per.values())
    steps.append('no per-slave override (404) for all shared codes: %s (%s)'
                 % (no_file, per))
    # absent from the /sync manifest
    m = json.loads(c.get(c.epm['sync_url'], timeout=30)[1])
    not_in_manifest = not any(k.startswith('shared/%s/' % empty) for k in m)
    steps.append('absent from /sync manifest: %s' % not_in_manifest)
    # a master (operator/cluster) page is NOT pushed down as a per-slave override
    op_no_pushdown = True
    try:
      for code in SHARED_CODES:
        c.put(op + code, '<html>OPERATOR %s</html>' % code)
      for code in SHARED_CODES:
        if c.get('%s/shared/%s/%s.http' % (base, empty, code))[0] != 404:
          op_no_pushdown = False
    finally:
      for code in SHARED_CODES:
        c.delete(op + code)
    steps.append('operator/cluster page NOT pushed down as per-slave override '
                 '(stays 404): %s' % op_no_pushdown)
    passed = no_file and not_in_manifest and op_no_pushdown
  finally:
    for code in SHARED_CODES:
      c.delete(up + code)
      c.delete(op + code)
  return _result(
      'M15', 'Urlless slave has no master override (accepted corner case)',
      'design decision — materialising per-slave overrides for every slave had '
      'bad impact, so urlless slaves get no master override',
      'a urlless/parameterless slave has no per-slave file and no manifest entry '
      'for 502/503/504, and an operator page is not pushed down to it',
      '; '.join(steps), passed)


# --------------------------------------------------------------------------- #
# Runner + report
# --------------------------------------------------------------------------- #
def _safe(mid, title, thunk):
  """Run a scenario, converting any exception into a FAIL result so one
  broken scenario never aborts the run or loses the report."""
  try:
    return thunk()
  except Exception as e:
    return _result(mid, title, '(scenario raised)', '(none)',
                   'EXCEPTION: %r' % e, False)


def run(phase, c, restart):
  results = []
  if phase == 'baseline':
    # Each resilience scenario starts from a freshly-restarted, responsive
    # manager so it independently demonstrates the pre-fix failure.
    restart()
    results.append(_safe('M1', 'Manifest lists cluster defaults + zero shared '
                         'overrides', lambda: m1_manifest_no_shared(c)))
    restart()
    results.append(_safe('M9', 'Concurrent /sync clients all served without '
                         'error', lambda: m9_concurrent(c)))
    restart()
    results.append(_safe('M8', 'Stalled clients do not wedge the manager',
                         lambda: m8_stalled_client(c, phase)))
    return results
  # full
  restart()
  plan = [
      ('M1', 'Manifest lists cluster defaults + zero shared overrides',
       lambda: m1_manifest_no_shared(c)),
      ('M2', 'Slave override adds exactly one manifest key',
       lambda: m2_manifest_override(c)),
      ('M3', 'Seed created cluster files + fallback symlinks',
       lambda: m3_seed_symlinks(c)),
      ('M4', 'Backends down + no override -> cluster 503 served',
       lambda: m4_frontend_serves_cluster_fallback(c)),
      ('M5', 'Slave without override inherits the cluster page',
       lambda: m5_new_slave_inherits_cluster(c)),
      ('M11', 'Operator page updates cluster file, not per-slave',
       lambda: m11_operator_change_not_per_slave(c)),
      ('M12', 'Operator delete reverts cluster to builtin',
       lambda: m12_operator_delete_reverts(c)),
      ('M13', 'Removed-slave overrides pruned, active kept',
       lambda: m13_prune(c)),
      ('M14', 'Slave override precedence over operator, all slave codes',
       lambda: m14_slave_override_precedence(c)),
      ('M15', 'Urlless slave has no master override (accepted corner case)',
       lambda: m15_urlless_slave_has_no_master_override(c)),
      ('M8', 'Stalled clients do not wedge the manager',
       lambda: m8_stalled_client(c, phase)),
      ('M9', 'Concurrent /sync clients all served without error',
       lambda: m9_concurrent(c)),
      ('M10', 'Stalled connection reaped by socket timeout',
       lambda: m10_timeout_reaping(c)),
  ]
  for mid, title, thunk in plan:
    results.append(_safe(mid, title, thunk))
  # slow lifecycle (two polling cycles) last
  try:
    results.extend(_lifecycle_override(c))
  except Exception as e:
    results.append(_result('M6', 'Override replaces fallback symlink', '',
                           '', 'EXCEPTION: %r' % e, False))
    results.append(_result('M7', 'Reset restores fallback symlink', '',
                           '', 'EXCEPTION: %r' % e, False))
  results.sort(key=lambda r: int(r['id'][1:]))
  return results


def render_report(phase, results, params, sr_id, note):
  now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  def sym(p):
    return {True: 'PASS', False: 'FAIL', None: 'N/A'}[p]
  npass = sum(1 for r in results if r['passed'] is True)
  nfail = sum(1 for r in results if r['passed'] is False)
  nna = sum(1 for r in results if r['passed'] is None)
  lines = []
  lines.append('# MR 2159 EPM e2e report — %s run' % phase)
  lines.append('')
  lines.append('- **Date:** %s' % now)
  lines.append('- **Bug:** `bug_module/20260722-9BC510` — rapid-cdn EPM '
               'resilience & scalability')
  lines.append('- **MR:** !2159 `fix/rapid-cdn-epm-rewrite`')
  lines.append('- **Software release:** `%s`' % params.get('software_cfg'))
  lines.append('- **SR build id:** `%s`' % sr_id)
  lines.append('- **EPM:** `%s`  **frontend:** `[%s]:%s`' % (
      params['epm'].get('url'),
      (params.get('frontend') or {}).get('https_ip'),
      (params.get('frontend') or {}).get('https_port')))
  lines.append('- **Slaves:** %s' % ', '.join(
      s['ref'] for s in (params.get('frontend') or {}).get('slaves', [])))
  lines.append('- **Summary:** %d PASS, %d FAIL, %d N/A' % (npass, nfail, nna))
  if note:
    lines.append('')
    lines.append('> %s' % note)
  lines.append('')
  lines.append('| # | Scenario | Result |')
  lines.append('|---|----------|--------|')
  for r in results:
    lines.append('| %s | %s | **%s** |' % (r['id'], r['title'], sym(r['passed'])))
  lines.append('')
  for r in results:
    lines.append('## %s — %s  (%s)' % (r['id'], r['title'], sym(r['passed'])))
    lines.append('')
    lines.append('- **Basis (MR test):** `%s`' % r['basis'])
    lines.append('- **Expected:** %s' % r['expected'])
    lines.append('- **Observed:** %s' % r['observed'])
    lines.append('')
  return '\n'.join(lines)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--params', required=True)
  ap.add_argument('--phase', choices=['baseline', 'full'], required=True)
  ap.add_argument('--report', required=True)
  ap.add_argument('--sr-id', default='unknown')
  ap.add_argument('--note', default='')
  ap.add_argument('--restart-cmd', default='',
                  help='shell command to restart the EPM before resilience '
                       'scenarios (baseline demonstrations start responsive)')
  args = ap.parse_args()

  with open(args.params) as f:
    params = json.load(f)
  c = Ctx(params)

  def restart():
    if args.restart_cmd:
      import subprocess
      subprocess.run(args.restart_cmd, shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      time.sleep(2)
    ready = c.wait_ready()
    print('[restart] manager ready=%s' % ready)

  try:
    results = run(args.phase, c, restart)
  finally:
    c.close()

  report = render_report(args.phase, results, params, args.sr_id, args.note)
  with open(args.report, 'w') as f:
    f.write(report + '\n')

  print('=== %s run ===' % args.phase)
  for r in results:
    print('%-4s %-5s %s' % (
        r['id'], {True: 'PASS', False: 'FAIL', None: 'N/A'}[r['passed']],
        r['title']))
    print('       observed: %s' % r['observed'])
  print('report written to', args.report)
  nfail = sum(1 for r in results if r['passed'] is False)
  return 0 if nfail == 0 else 1


if __name__ == '__main__':
  raise SystemExit(main())
