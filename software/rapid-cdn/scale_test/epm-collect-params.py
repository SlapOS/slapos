# slapos console collector for the on-node EPM harness (epm-e2e.py,
# scale-validate.py, epm-chaos-test.py).
#
# Run with:
#   /opt/slapos/bin/slapos console --cfg /etc/opt/slapos/slapos.cfg \
#       scale_test/epm-collect-params.py
#
# 'slap' is injected by slapos console.  Emits a single JSON document to
# OUT_PATH describing every endpoint / on-disk path the harness needs, so the
# harness itself stays a plain python3 script with no slapos dependency.
# Override the node id with RAPIDCDN_COMPUTER_ID and the partition root with
# RAPIDCDN_PARTITION_ROOT for a non-default node.
import glob
import json
import os
import re

COMPUTER_ID = os.environ.get('RAPIDCDN_COMPUTER_ID', 'local_computer')
PARTITION_ROOT = os.environ.get('RAPIDCDN_PARTITION_ROOT', '/srv/slapgrid')
OUT_PATH = os.environ.get(
    'EPM_PARAMS_OUT',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'epm-params.json'))


def _partition_root(partition_id):
  # Partitions live at <PARTITION_ROOT>/<partition_id> (default /srv/slapgrid).
  return os.path.join(PARTITION_ROOT, partition_id)


def _find_https_bind(partition_root):
  """Parse the frontend-haproxy config for the first `bind <ipv6>:<port> ssl`."""
  for cfg in glob.glob(
      os.path.join(partition_root, 'etc', '*frontend-haproxy*.cfg')):
    try:
      with open(cfg) as f:
        text = f.read()
    except OSError:
      continue
    # bind fd46::5:4443 ssl  (IPv6 literal, no brackets in haproxy config)
    m = re.search(r'^\s*bind\s+([0-9a-fA-F:]+):(\d+)\s+ssl', text, re.MULTILINE)
    if m:
      return m.group(1), int(m.group(2))
  return None, None


data = {
    'computer_id': COMPUTER_ID,
    'software_cfg': os.environ.get(
        'RAPIDCDN_SOFTWARE', '/opt/slapos.git/software/rapid-cdn/software.cfg'),
    'epm': None,
    'frontend': None,       # first frontend (back-compat for the 13-scenario harness)
    'frontends': [],        # all frontend partitions (scale test)
    'cluster_master_operator_url': None,
}

computer = slap.registerComputer(COMPUTER_ID)
for cp in computer.getComputerPartitionList():
  pid = cp.getId()
  try:
    conn = cp.getConnectionParameterDict()
  except Exception:
    conn = {}
  if not conn:
    continue
  try:
    ptype = cp.getType()
  except Exception:
    ptype = ''

  if ptype == 'default' and 'error-page-manager-operator-url' in conn:
    data['cluster_master_operator_url'] = conn['error-page-manager-operator-url']

  if ptype == 'error-page-manager':
    inner = json.loads(conn['_'])
    read_token = inner['sync-url'].rstrip('/').rsplit('/', 1)[-1]
    host_port = re.search(r'https://\[([^\]]+)\]:(\d+)', inner['sync-url'])
    shared = {
        ref: {'upload_url': info['upload-url']}
        for ref, info in json.loads(
            inner['shared-error-page-information']).items()
    }
    data['epm'] = {
        'partition': pid,
        'base_url': inner['base-url'],
        'sync_url': inner['sync-url'],
        'operator_url': inner['operator-url'],
        'url': inner['url'],
        'read_token': read_token,
        'host': host_port.group(1) if host_port else None,
        'port': int(host_port.group(2)) if host_port else None,
        'certificate': inner['certificate'],
        'shared': shared,
    }

  # The frontend/slave-list partition carries slave-instance-information-list
  # and hosts the error-page-updater + seed.
  if '_' in conn:
    try:
      inner = json.loads(conn['_'])
    except (ValueError, TypeError):
      inner = {}
    if isinstance(inner, dict) and 'slave-instance-information-list' in inner:
      root = _partition_root(pid)
      updater_cfg = os.path.join(root, 'etc', 'error-page-updater.json')
      error_pages_dir = builtin_dir = None
      if os.path.isfile(updater_cfg):
        with open(updater_cfg) as f:
          uc = json.load(f)
        error_pages_dir = os.path.normpath(uc.get('error_pages_dir', ''))
        builtin_dir = os.path.normpath(uc.get('builtin_dir', ''))
      https_ip, https_port = _find_https_bind(root)
      slaves = [
          {'ref': s['slave-reference'], 'domain': s['domain']}
          for s in json.loads(inner['slave-instance-information-list'])
      ]
      fe = {
          'partition': pid,
          'root': root,
          'https_ip': https_ip,
          'https_port': https_port,
          'error_pages_dir': error_pages_dir,
          'builtin_dir': builtin_dir,
          'slaves': slaves,
      }
      data['frontends'].append(fe)
      if data['frontend'] is None:
        data['frontend'] = fe

with open(OUT_PATH, 'w') as f:
  json.dump(data, f, indent=2)
print('wrote', OUT_PATH)
print(json.dumps(
    {k: (v if not isinstance(v, dict) else '<dict>') for k, v in data.items()},
    indent=2))
