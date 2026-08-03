# slapos console: request the MIXED-SR rapid-cdn cluster (mirrors
# mixed_sr_test/test_mixed_sr.py):
#   - cluster + frontend-1 + kedifa + error-page-manager on the NEW (MR) SR
#   - frontend-2 pinned to the OLD 1.0.469 release
# EPM_FE1_STATE / EPM_FE2_STATE default 'started'.
import json
import os

SOFTWARE_NEW = os.environ.get(
    'RAPIDCDN_SOFTWARE', '/opt/slapos.git/software/rapid-cdn/software.cfg')
# Last released rapid-cdn tag, from the canonical binary-cached /-/raw/ URL
# (see CAVEATS.md: the non-canonical /raw/ form is not in the binary cache).
OLD_URL = os.environ.get(
    'RAPIDCDN_OLD_SOFTWARE',
    'https://lab.nexedi.com/nexedi/slapos/-/raw/1.0.469'
    '/software/rapid-cdn/software.cfg')
f1 = os.environ.get('EPM_FE1_STATE', 'started')
f2 = os.environ.get('EPM_FE2_STATE', 'started')

cluster = request(
    SOFTWARE_NEW,
    'scale-cluster',
    software_type='default',
    partition_parameter_kw={'_': json.dumps({
        'domain': 'example.org',
        '-frontend-quantity': 2,
        '-sla-2-computer_guid': 'local_computer',
        '-frontend-2-software-release-url': OLD_URL,
        '-frontend-1-state': f1,
        '-frontend-2-state': f2,
    })},
)
print('requested mixed scale-cluster: frontend-1=%s (NEW/MR), '
      'frontend-2=%s (OLD 1.0.469)' % (f1, f2))
