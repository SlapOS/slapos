# -*- coding: utf-8 -*-

import logging
import time

import slapos

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)



class Renamer(object):
    def __init__(self, server_url, key_file, cert_file, computer_guid,
                 partition_id, software_release, namebase):
        self.server_url = server_url
        self.key_file = key_file
        self.cert_file = cert_file
        self.computer_guid = computer_guid
        self.partition_id = partition_id
        self.software_release = software_release
        self.namebase = namebase


    def _failover(self):
        """\
        This method does

        - retrieve the broken computer partition
        - change its reference to 'broken-...' and its software type to 'frozen'
        - retrieve the winner computer partition (attached to this process)
        - change its reference to replace the broken one.
          later, slapgrid will change its software_type as well.

        Then, after running slapgrid-cp a few times, the winner takes over and
        a new cp is created to replace it as an importer.
        """

        slap = slapos.slap.slap()
        slap.initializeConnection(self.server_url, self.key_file, self.cert_file)

        # partition that will take over.
        cp_winner = slap.registerComputerPartition(computer_guid=self.computer_guid,
                                                   partition_id=self.partition_id)
        # XXX although we can already rename cp_winner, to change its software type we need to
        # get hold of the root cp as well

        cp_exporter_ref = self.namebase + '0'       # this is ok. the boss is always number zero.

        # partition to be deactivated
        cp_broken = cp_winner.request(software_release=self.software_release,
                                      software_type='frozen',
                                      state='stopped',
                                      partition_reference=cp_exporter_ref)

        broken_new_ref = 'broken-{}'.format(time.strftime("%d-%b_%H:%M:%S", time.gmtime()))

        log.debug("Renaming {}: {}".format(cp_broken.getId(), broken_new_ref))

        cp_broken.rename(new_name=broken_new_ref)

        log.debug("Renaming {}: {}".format(cp_winner.getId(), cp_exporter_ref))

        # update name (and later, software type) for the partition that will take over

        cp_winner.rename(new_name=cp_exporter_ref)
        cp_winner.bang(message='partitions have been renamed!')



    def failover(self):
        try:
            self._failover()
            log.info('Renaming done')
        except slapos.slap.ServerError:
            log.info('Internal server error')

