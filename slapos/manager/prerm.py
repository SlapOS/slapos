# coding: utf-8
import logging
import os
import sys
import subprocess

from zope import interface as zope_interface
from slapos.manager import interface
from slapos.grid.slapgrid import COMPUTER_PARTITION_WAIT_LIST_FILENAME

logger = logging.getLogger(__name__)

class Manager(object):
  """Manager is called in every step of preparation of the computer."""

  zope_interface.implements(interface.IManager)

  def __init__(self, config):
    """Manager needs to know config for its functioning.
    """
    pass

  def format(self, computer):
    """Method called at `slapos node format` phase.
    """
    pass

  def formatTearDown(self, computer):
    """Method called after `slapos node format` phase.

    :param computer: slapos.format.Computer, formatted computer
    """
    pass

  def software(self, software):
    """Method called at `slapos node software` phase.
    """
    pass

  def softwareTearDown(self, software):
    """Method called after `slapos node software` phase.

    :param computer: slapos.grid.SlapObject.Software, processed software
    """
    pass

  def instance(self, partition):
    """Method called at `slapos node instance` phase.
    """
    pass

  def instanceTearDown(self, partition):
    """Method  called after `slapos node instance` phase.

    :param partition: slapos.grid.SlapObject.Partition, processed partition
    """
    pass

  def report(self, partition):
    """Method called at `slapos node report` phase."""

    partition.createRetentionLockDate()
    if not partition.checkRetentionIsAuthorized():
      return

    wait_filepath = os.path.join(partition.instance_path,
                                 COMPUTER_PARTITION_WAIT_LIST_FILENAME)
    if not os.path.exists(partition.prerm_path):
      return
    partition_id = partition.partition_id
    wrapper_list = [f for f in os.listdir(partition.prerm_path)
                    if os.path.isfile(os.path.join(partition.prerm_path, f))]
    if len(wrapper_list) > 0:
      group_suffix = "prerm"
      logger.info("Adding pre-delete scripts to supervisord...")
      partition.generateSupervisorConfiguration()
      partition.addServiceToCustomGroup(group_suffix,
                                        partition_id,
                                        wrapper_list,
                                        partition.prerm_path)
      partition.writeSupervisorConfigurationFile()

      # check the state of all process, if the process is not started yes, start it
      supervisord = partition.getSupervisorRPC()
      process_list_string = ""
      for name in wrapper_list:
        process_name = '-'.join([partition_id, group_suffix]) + ':' + name
        process_list_string += '%s\n' % process_name
        status = supervisord.getProcessInfo(process_name)
        if status['start'] == 0:
          # process is not started yet
          logger.info("Starting pre-delete process %r..." % name)
          supervisord.startProcess(process_name, False)

      # ask to slapgrid to check theses scripts before destroy partition
      with open(wait_filepath, 'w') as f:
        f.write(process_list_string)
