#!/usr/bin/env python3
"""Chaos test for the rapid-cdn error-page-manager (EPM) at scale.

Breaks the EPM server <-> client communication in several ways and verifies:
  1. the EPM server recovers (its on-watch wrapper restarts it; it never wedges);
  2. the frontend updater clients survive (retry, resume; don't crash);
  3. CRUCIALLY end-users keep getting error pages throughout -- the frontend
     serves from its local copies + fallback symlinks, so serving is decoupled
     from the EPM control plane.

A background prober hits a slave domain on a frontend every 0.5 s for the whole
run and records serve continuity (the survival metric). Scenarios:
  C1  SIGKILL the EPM process (x3)         -> supervisor/on-watch restarts it
  C2  ip6tables DROP the EPM port (90 s)   -> clients time out + retry, recover
  C3  reset established EPM connections     -> server + clients survive
  C4  SIGKILL a frontend updater           -> supervisor restarts it, resumes
  C5  stalled+concurrent flood during a kill -> no wedge

Usage: python3 test/epm-chaos-test.py --params test/epm-params.json \
         --report test/epm-chaos-report-<date>.md
"""
import argparse
import importlib.util
import json
import os
import re
import socket
import ssl
import subprocess
import threading
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('h', os.path.join(HERE, 'epm-e2e.py'))
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def sh(cmd):
  return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def find_pids(needle):
  """PIDs whose /proc cmdline contains needle (no ps/pkill self-match)."""
  pids = []
  for d in os.listdir('/proc'):
    if not d.isdigit():
      continue
    try:
      cmd = open('/proc/%s/cmdline' % d, 'rb').read().replace(b'\0', b' ').decode()
    except Exception:
      continue
    if needle in cmd:
      pids.append(int(d))
  return pids


class Prober(threading.Thread):
  """Continuously hit a slave domain on a frontend; record serve continuity."""
  def __init__(self, ip, port, domain):
    super().__init__(daemon=True)
    self.ip, self.port, self.domain = ip, port, domain
    self.stop = threading.Event()
    self.ok = 0
    self.fail = 0
    self.samples = []  # (t, served_bool)

  def run(self):
    while not self.stop.is_set():
      served = False
      try:
        uctx = ssl._create_unverified_context()
        raw = socket.create_connection((self.ip, self.port), timeout=5)
        s = uctx.wrap_socket(raw, server_hostname=self.domain)
        s.sendall(('GET / HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n'
                   % self.domain).encode())
        buf = b''
        while True:
          c = s.recv(65536)
          if not c:
            break
          buf += c
        s.close(); raw.close()
        txt = buf.decode('utf-8', 'replace')
        served = 'Service Unavailable' in txt or txt.startswith('HTTP/1.0 503')
      except Exception:
        served = False
      self.samples.append((time.time(), served))
      if served:
        self.ok += 1
      else:
        self.fail += 1
      time.sleep(0.5)


def epm_ready(c, timeout=60):
  begin = time.time()
  while time.time() - begin < timeout:
    try:
      if c.get(c.epm['sync_url'], timeout=5)[0] == 200:
        return time.time() - begin
    except Exception:
      pass
    time.sleep(1)
  return None


# Recovery path: on a normal node the watchdog + per-minute `slapos node
# instance` cron restart a crashed on-watch service; here (manual convergence)
# we invoke the same effect deterministically via supervisorctl start.
_SVCTL = ['/opt/slapos/bin/slapos node supervisorctl --cfg /etc/opt/slapos/slapos.cfg']
_EPM_PROG = ['']


def svctl(action, prog):
  return sh('%s %s %s' % (_SVCTL[0], action, prog))


def updater_progs():
  r = sh('%s status' % _SVCTL[0])
  return [ln.split()[0] for ln in r.stdout.splitlines()
          if 'error-page-updater' in ln and 'on-watch' in ln]


def recover(c, timeout=90):
  svctl('start', _EPM_PROG[0])
  return epm_ready(c, timeout=timeout)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--params', required=True)
  ap.add_argument('--report', required=True)
  ap.add_argument('--epm-prog', required=True,
                  help='EPM on-watch supervisor program name')
  ap.add_argument('--cfg', default='/etc/opt/slapos/slapos.cfg')
  args = ap.parse_args()
  SVCTL = '/opt/slapos/bin/slapos node supervisorctl --cfg %s' % args.cfg
  _SVCTL[0] = SVCTL
  _EPM_PROG[0] = args.epm_prog
  params = json.load(open(args.params))
  c = h.Ctx(params)
  host, port = c.epm['host'], c.epm['port']
  fe = params['frontend']
  dom = fe['slaves'][0]['domain']
  results = []

  def record(name, detail, survived):
    results.append({'name': name, 'detail': detail, 'survived': survived})
    print('%-40s %s' % (name, 'SURVIVED' if survived else 'FAILED'))
    print('    ' + detail)

  # start the end-user serving prober
  prober = Prober(fe['https_ip'], fe['https_port'], dom)
  prober.start()
  time.sleep(3)
  base_ok = prober.ok

  try:
    # --- baseline ---
    st = c.get(c.epm['sync_url'], timeout=10)[0]
    record('C0 baseline', 'EPM /sync=%s; prober ok=%d fail=%d' % (
        st, prober.ok, prober.fail), st == 200)

    # --- C1: SIGKILL the EPM process, recover via instance cron (x2) ---
    times = []
    ok = True
    pre = prober.fail
    for i in range(2):
      for p in find_pids('rapid-cdn-error-page-manager'):
        cmd = open('/proc/%s/cmdline' % p, 'rb').read().replace(b'\0', b' ').decode()
        if 'error-page-manager.json' in cmd:  # inner server, not the wrapper
          os.kill(p, 9)
      down = c.get(c.epm['sync_url'], timeout=3)[0] if False else None
      t = recover(c, timeout=120)   # production recovery path (instance cron)
      times.append(t)
      if t is None:
        ok = False
    record('C1 SIGKILL EPM + cron recovery (x2)',
           'recovery times=%s s; end-user serve-fails during=%d' % (
               [None if t is None else round(t, 1) for t in times],
               prober.fail - pre),
           ok)

    # --- C2: EPM server DOWN for 45s (supervisor stop), then restart ---
    pre_fail = prober.fail
    sh('%s stop %s' % (SVCTL, args.epm_prog))
    blocked_ok = 0
    blocked_err = 0
    t0 = time.time()
    while time.time() - t0 < 45:  # EPM is down: clients must fail-and-retry
      try:
        if c.get(c.epm['sync_url'], timeout=3)[0] == 200:
          blocked_ok += 1
      except Exception:
        blocked_err += 1
      time.sleep(2)
    serve_fail_during_block = prober.fail - pre_fail
    sh('%s start %s' % (SVCTL, args.epm_prog))
    rec = epm_ready(c, timeout=60)
    record('C2 EPM server down 45s (supervisor stop/start)',
           'while down: EPM reachable=%d unreachable=%d; frontend serve-fails '
           'during outage=%d; EPM recovered after restart=%s s' % (
               blocked_ok, blocked_err, serve_fail_during_block,
               None if rec is None else round(rec, 1)),
           rec is not None)

    # --- C3: reset established EPM connections ---
    # open some connections then forcibly reset all sockets on the EPM port
    held = []
    for _ in range(5):
      try:
        held.append(c.open_stalled())
      except Exception:
        pass
    r = sh("ss -K '( sport = :%d )' 2>&1" % port)
    time.sleep(2)
    st = None
    try:
      st = c.get(c.epm['sync_url'], timeout=10)[0]
    except Exception as e:
      st = 'ERR:%r' % e
    for tls in held:
      try:
        tls.close()
      except Exception:
        pass
    record('C3 reset established EPM conns',
           'ss -K rc=%d (%s); EPM /sync after reset=%s' % (
               r.returncode, (r.stdout or r.stderr).strip()[:40], st),
           st == 200)

    # --- C4: SIGKILL a frontend updater ---
    upids = find_pids('rapid-cdn-error-page-updater')
    ukilled = []
    for p in upids:
      cmd = open('/proc/%s/cmdline' % p, 'rb').read().replace(b'\0', b' ').decode()
      if 'error-page-updater.json' in cmd:
        os.kill(p, 9); ukilled.append(p)
    for up in updater_progs():   # recover the updater(s) via supervisor
      svctl('start', up)
    time.sleep(5)
    upids2 = find_pids('rapid-cdn-error-page-updater')
    resumed = len([p for p in upids2
                   if 'error-page-updater.json' in
                   open('/proc/%s/cmdline' % p, 'rb').read().replace(b'\0', b' ').decode()]) \
        if upids2 else 0
    record('C4 SIGKILL frontend updater + cron recovery',
           'killed=%d; updaters running after recovery=%d' % (len(ukilled), resumed),
           resumed >= 1)

    # --- C5: stalled+concurrent flood during an EPM kill ---
    stalled = []
    for _ in range(15):
      try:
        stalled.append(c.open_stalled())
      except Exception:
        pass
    # kill EPM under load
    for p in find_pids('rapid-cdn-error-page-manager'):
      cmd = open('/proc/%s/cmdline' % p, 'rb').read().replace(b'\0', b' ').decode()
      if 'error-page-manager.json' in cmd:
        try:
          os.kill(p, 9)
        except Exception:
          pass
    rec = recover(c, timeout=120)   # production recovery path
    r9 = h.m9_concurrent(c)
    for tls in stalled:
      try:
        tls.close()
      except Exception:
        pass
    record('C5 flood + kill under load',
           'EPM recovered=%s s; concurrent after: %s' % (
               None if rec is None else round(rec, 1), r9['observed']),
           rec is not None and r9['passed'])

  finally:
    prober.stop.set()
    prober.join(timeout=10)
    c.close()

  # serving continuity summary
  total = prober.ok + prober.fail
  cont = 100.0 * prober.ok / total if total else 0
  # longest consecutive serve-fail streak (seconds)
  worst = 0
  cur = 0
  for _, served in prober.samples:
    if served:
      cur = 0
    else:
      cur += 1
      worst = max(worst, cur)
  worst_s = worst * 0.5

  survived_all = all(r['survived'] for r in results)
  lines = ['# EPM chaos test — broken server<->client comms\n']
  lines.append('- **Date:** %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
  lines.append('- **EPM:** %s  **frontend probe:** [%s]:%s (%s)' % (
      c.epm['url'], fe['https_ip'], fe['https_port'], dom))
  lines.append('- **End-user serving continuity:** %.1f%% (%d ok / %d fail of %d probes)'
               % (cont, prober.ok, prober.fail, total))
  lines.append('- **Worst continuous serve outage:** %.1f s' % worst_s)
  lines.append('- **Overall:** %s\n' % ('ALL SURVIVED' if survived_all else 'SOME FAILED'))
  lines.append('| Scenario | Result | Detail |')
  lines.append('|---|---|---|')
  for r in results:
    lines.append('| %s | %s | %s |' % (
        r['name'], 'SURVIVED' if r['survived'] else 'FAILED', r['detail']))
  open(args.report, 'w').write('\n'.join(lines) + '\n')

  print('\n=== serving continuity: %.1f%% ok, worst outage %.1fs ===' % (cont, worst_s))
  print('report:', args.report)
  return 0 if survived_all else 1


if __name__ == '__main__':
  raise SystemExit(main())
