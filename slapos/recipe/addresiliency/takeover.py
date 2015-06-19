# -*- coding: utf-8 -*-
import logging
import time
import traceback

import slapos
from slapos.slap.slap import NotFoundError

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def takeover(server_url, key_file, cert_file, computer_guid,
             partition_id, software_release, namebase,
             winner_instance_suffix = None,
             takeover_triggered_file_path=None):
  """
  This function does

  - retrieve the broken computer partition
  - change its reference to 'broken-...' and its software type to 'frozen'
  - retrieve the winner computer partition (attached to this process)
  - change its reference to replace the broken one.
    later, slapgrid will change its software_type as well.

  Then, after running slapgrid-cp a few times, the winner takes over and
  a new cp is created to replace it as an importer.
  """

  slap = slapos.slap.slap()
  slap.initializeConnection(server_url, key_file, cert_file)
  current_partition = slap.registerComputerPartition(computer_guid=computer_guid,
                                                     partition_id=partition_id)

  # partition that will take over.
  if winner_instance_suffix:
    winner_instance_name = namebase + winner_instance_suffix
    # XXX: we hardcode a lot of values here, because request is a settergetter, all at once.
    cp_winner = current_partition.request(software_release=software_release,
                                  software_type='%s-import' % namebase,
                                  partition_reference=winner_instance_name)
  else:
    # This script is run in the winning partition: use this one as winner
    cp_winner = current_partition
  # XXX although we can already rename cp_winner, to change its software type we need to
  # get hold of the root cp as well

  cp_exporter_ref = namebase + '0'       # this is ok. the boss is always number zero.

  # partition to be deactivated
  cp_broken = cp_winner.request(software_release=software_release,
                                software_type='frozen',
                                state='stopped',
                                partition_reference=cp_exporter_ref)

  broken_new_ref = 'broken-{}'.format(time.strftime("%d-%b_%H:%M:%S", time.gmtime()))

  log.debug("Renaming {}: {}".format(cp_broken.getId(), broken_new_ref))

  cp_broken.rename(new_name=broken_new_ref)

  log.debug("Renaming {}: {}".format(cp_winner.getId(), cp_exporter_ref))

  # update name (and later, software type) for the partition that will take over
  while True:
    time.sleep(10)
    try:
      cp_winner.rename(new_name=cp_exporter_ref)
      break
    except NotFoundError:
      traceback.print_exc()
      log.warning('Impossible to rename. Retrying in a few seconds...')
  log.debug('Renamed.')

  cp_winner.bang(message='partitions have been renamed!')
  # Note: Root instance will reconfigure itself the winning instance (software_type
  # and parameters.)

  # Create "lock" file preventing equeue to run import scripts
  # XXX hardcoded
  open(takeover_triggered_file_path, 'w').write('')

def run(args):
  slapos.recipe.addresiliency.takeover.takeover(server_url = args.pop('server_url'),
                                                key_file = args.pop('key_file'),
                                                cert_file = args.pop('cert_file'),
                                                computer_guid = args.pop('computer_id'),
                                                partition_id = args.pop('partition_id'),
                                                software_release = args.pop('software'),
                                                namebase = args.pop('namebase'),
                                                takeover_triggered_file_path = args.pop('takeover_triggered_file_path'))

