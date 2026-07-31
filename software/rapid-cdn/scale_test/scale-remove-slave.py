# slapos console: destroy (remove) shared slaves by reference.
#   EPM_REMOVE_REFS="scale-slave-9999 scale-slave-9998" \
#     slapos console --cfg .../slapos.cfg scale-remove-slave.py
#
# Requesting a shared instance with state='destroyed' removes it; on the next
# converge the master drops it from authorized_slave_list, the EPM restarts on
# the config change and prunes its override (software._prune_removed_shared_overrides).
import os

SOFTWARE = os.environ.get(
    'RAPIDCDN_SOFTWARE', '/opt/slapos.git/software/rapid-cdn/software.cfg')
REFS = os.environ.get('EPM_REMOVE_REFS', '').split()

for ref in REFS:
  request(
      SOFTWARE,
      ref,
      software_type='default',
      shared=True,
      partition_parameter_kw={'url': 'http://[::1]:9080/'},
      state='destroyed',
  )
  print('destroyed', ref)
print('done: destroyed %d slave(s): %s' % (len(REFS), ' '.join(REFS)))
