# slapos console: request a standalone error-page-manager instance (no full
# cluster) with a couple of shared slaves — enough to exercise manager-level
# behaviour (operator/slave overrides, precedence). Mirrors test.TestErrorPageManager.
import json
import os

SOFTWARE = os.environ.get(
    'RAPIDCDN_SOFTWARE', '/opt/slapos.git/software/rapid-cdn/software.cfg')
inst = request(
    SOFTWARE,
    'epm-standalone',
    software_type='error-page-manager',
    partition_parameter_kw={'_': json.dumps({
        'monitor-password': 'test-monitor-password',
        'monitor-httpd-port': 25000,
        'shared-list': [
            {'slave_reference': 'test-slave-1'},
            {'slave_reference': 'test-slave-2'},
            {'slave_reference': 'test-slave-empty'},
        ],
    })},
)
print('requested epm-standalone (software_type=error-page-manager, 2 slaves)')
try:
  print('conn keys:', sorted(json.loads(
      inst.getConnectionParameterDict()['_']).keys()))
except Exception as e:
  print('not ready yet:', e)
