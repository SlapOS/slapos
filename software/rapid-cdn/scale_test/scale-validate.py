#!/usr/bin/env python3
"""Scale-rung validation + metrics for the 10k-slave EPM test.

Reuses the e2e harness helpers (Ctx, frontend_get, open_stalled). Measures, at
whatever slave count is currently deployed:
  - EPM /sync manifest: #cluster keys, #shared keys, response latency + bytes
  - EPM process: RSS, thread count
  - seed: per-frontend count of shared/<ref> dirs and fallback symlinks (+sanity)
  - serving: sample slave domains through every frontend (expect origin 200)
  - resilience: stalled-client probe + concurrent /sync burst
Appends a one-line metrics record to test/scale-metrics.csv and prints a summary.

  python3 test/scale-validate.py --params test/epm-params.json --label 100
"""
import argparse
import glob
import importlib.util
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('h', os.path.join(HERE, 'epm-e2e.py'))
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def epm_process_stats():
  """RSS (MiB) and thread count of the running error-page-manager process."""
  for status in glob.glob('/proc/*/status'):
    try:
      pid = status.split('/')[2]
      cmd = open('/proc/%s/cmdline' % pid, 'rb').read().replace(b'\0', b' ').decode()
    except Exception:
      continue
    if 'rapid-cdn-error-page-manager' in cmd or ('error_page_manager_main' in cmd):
      rss = threads = None
      for line in open(status):
        if line.startswith('VmRSS:'):
          rss = int(line.split()[1]) / 1024.0
        elif line.startswith('Threads:'):
          threads = int(line.split()[1])
      return {'pid': int(pid), 'rss_mib': round(rss, 1) if rss else None,
              'threads': threads}
  return {'pid': None, 'rss_mib': None, 'threads': None}


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--params', required=True)
  ap.add_argument('--label', required=True, help='slave-count label for this rung')
  ap.add_argument('--serve-sample', type=int, default=5)
  args = ap.parse_args()
  params = json.load(open(args.params))
  c = h.Ctx(params)
  out = {'label': args.label, 'ts': time.strftime('%Y-%m-%d %H:%M:%S')}
  try:
    # --- manifest ---
    t0 = time.time()
    raw = c.get(c.epm['sync_url'], timeout=60)
    dt = time.time() - t0
    manifest = json.loads(raw[1])
    cluster_keys = [k for k in manifest if k.startswith('cluster/')]
    shared_keys = [k for k in manifest if k.startswith('shared/')]
    out['manifest_cluster'] = len(cluster_keys)
    out['manifest_shared'] = len(shared_keys)
    out['manifest_bytes'] = len(raw[1])
    out['sync_latency_ms'] = round(dt * 1000, 1)

    # --- EPM process ---
    out.update({'epm_%s' % k: v for k, v in epm_process_stats().items()})

    # --- seed symlinks across all frontends ---
    fe_reports = []
    total_links = 0
    link_problems = 0
    for fe in params.get('frontends', []):
      epd = fe.get('error_pages_dir')
      shared_dir = os.path.join(epd, 'shared') if epd else None
      refs = os.listdir(shared_dir) if shared_dir and os.path.isdir(shared_dir) else []
      links = 0
      for ref in refs:
        for code in ('502', '503', '504'):
          p = os.path.join(shared_dir, ref, code + '.http')
          if os.path.islink(p):
            links += 1
            if os.readlink(p) != os.path.join('..', '..', 'cluster', code + '.http') \
               or not os.path.isfile(p):
              link_problems += 1
      total_links += links
      fe_reports.append('%s:%drefs/%dlinks' % (fe['partition'], len(refs), links))
    out['seed_total_symlinks'] = total_links
    out['seed_link_problems'] = link_problems
    out['seed_per_frontend'] = ' '.join(fe_reports)

    # --- serving sample through every frontend ---
    slaves = (params.get('frontend') or {}).get('slaves', [])
    sample = slaves[:args.serve_sample]
    serve_ok = serve_total = 0
    serve_detail = []
    for fe in params.get('frontends', []):
      ip, port = fe['https_ip'], fe['https_port']
      for s in sample:
        serve_total += 1
        try:
          # reuse frontend_get but against this specific frontend ip/port
          import ssl
          import socket
          uctx = ssl._create_unverified_context()
          raw2 = socket.create_connection((ip, port), timeout=15)
          ss = uctx.wrap_socket(raw2, server_hostname=s['domain'])
          ss.sendall(('GET / HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n'
                      % s['domain']).encode())
          buf = b''
          while True:
            ch = ss.recv(65536)
            if not ch:
              break
            buf += ch
          ss.close(); raw2.close()
          txt = buf.decode('utf-8', 'replace')
          st = txt.split('\r\n', 1)[0].split()[1] if txt else '?'
          # Backends are down (EPM error-page path): the frontend must serve the
          # EPM 503 page. (If fronting a live origin instead, accept 200+origin.)
          if (st == '503' and 'Service Unavailable' in txt) or \
             (st == '200' and 'scale-origin OK' in txt):
            serve_ok += 1
        except Exception:
          pass
    out['serve_ok'] = serve_ok
    out['serve_total'] = serve_total

    # --- resilience ---
    r8 = h.m8_stalled_client(c, 'full')
    r9 = h.m9_concurrent(c)
    out['stalled_ok'] = r8['passed']
    out['concurrent'] = r9['observed']
  finally:
    c.close()

  # append CSV
  csv = os.path.join(HERE, 'scale-metrics.csv')
  cols = ['label', 'ts', 'manifest_cluster', 'manifest_shared', 'manifest_bytes',
          'sync_latency_ms', 'epm_rss_mib', 'epm_threads', 'seed_total_symlinks',
          'seed_link_problems', 'serve_ok', 'serve_total', 'stalled_ok']
  newfile = not os.path.exists(csv)
  with open(csv, 'a') as f:
    if newfile:
      f.write(','.join(cols) + '\n')
    f.write(','.join(str(out.get(c2, '')) for c2 in cols) + '\n')

  print('=== scale rung: %s slaves ===' % args.label)
  for k in cols[2:]:
    print('  %-20s %s' % (k, out.get(k)))
  print('  seed_per_frontend    %s' % out.get('seed_per_frontend'))
  print('  concurrent           %s' % out.get('concurrent'))


if __name__ == '__main__':
  raise SystemExit(main())
