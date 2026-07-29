# slapos console: request a range of shared slaves for the scale cluster.
#   EPM_SLAVE_START=1 EPM_SLAVE_COUNT=100 EPM_SLAVE_URL=http://[::1]:9080/ \
#     slapos console --cfg .../slapos.cfg scale-request-slaves.py
#
# Slaves are shared instances of scale-cluster; each 'scale-slave-N' gets an
# auto-derived domain. Default backend is the shared scale origin (real 200s);
# set EPM_SLAVE_URL=down to point at a non-listening address (503 / error page).
# Override the software release with RAPIDCDN_SOFTWARE for a non-default checkout.
import os
import time

SOFTWARE = os.environ.get(
    'RAPIDCDN_SOFTWARE', '/opt/slapos.git/software/rapid-cdn/software.cfg')
START = int(os.environ.get('EPM_SLAVE_START', '1'))
COUNT = int(os.environ.get('EPM_SLAVE_COUNT', '100'))
URL = os.environ.get('EPM_SLAVE_URL', 'http://[::1]:9080/')
if URL == 'down':
  URL = 'http://[::1]:1/'

t0 = time.time()
end = START + COUNT
for n in range(START, end):
  request(
      SOFTWARE,
      'scale-slave-%d' % n,
      software_type='default',
      shared=True,
      partition_parameter_kw={'url': URL},
  )
  if (n - START + 1) % 500 == 0:
    print('  requested %d/%d (%.1fs)' % (n - START + 1, COUNT, time.time() - t0))
print('done: requested scale-slave-%d..%d (%d) in %.1fs, url=%s'
      % (START, end - 1, COUNT, time.time() - t0, URL))
