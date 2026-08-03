# slapos console: request the rapid-cdn scale cluster with N frontend nodes.
#   EPM_FRONTEND_QTY=4 slapos console --cfg .../slapos.cfg scale-request-cluster.py
# Override the software release with RAPIDCDN_SOFTWARE for a non-default checkout.
import json
import os

SOFTWARE = os.environ.get(
    'RAPIDCDN_SOFTWARE', '/opt/slapos.git/software/rapid-cdn/software.cfg')
QTY = int(os.environ.get('EPM_FRONTEND_QTY', '4'))

cluster = request(
    SOFTWARE,
    'scale-cluster',
    software_type='default',
    partition_parameter_kw={'_': json.dumps({
        'domain': 'example.org',
        '-frontend-quantity': QTY,
    })},
)
print('requested scale-cluster with -frontend-quantity=%d' % QTY)
try:
  print('connection params:', json.dumps(
      cluster.getConnectionParameterDict(), indent=1)[:400])
except Exception as e:
  print('not ready yet:', e)
