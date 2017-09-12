# coding: utf-8
import logging
import os
import sys
import subprocess

from zope import interface as zope_interface
from slapos.manager import interface
from slapos.grid.slapgrid import COMPUTER_PARTITION_WAIT_LIST_FILENAME

logger = logging.getLogger(__name__)
WIPE_WRAPPER_BASE_PATH = "var/run/slapos/pre-destroy/"

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

  def software(self, software):
    """Method called at `slapos node software` phase.
    """
    pass

  def instance(self, partition):
    """Method called at `slapos node instance` phase.
    """
    pass

  def report(self, partition):
    """Method called at `slapos node report` phase."""

    partition.createRetentionLockDate()
    if not partition.checkRetentionIsAuthorized():
      return

    wait_filepath = os.path.join(partition.instance_path,
                                 COMPUTER_PARTITION_WAIT_LIST_FILENAME)
    wipe_base_folder = os.path.join(partition.instance_path,
                                    WIPE_WRAPPER_BASE_PATH)
    if not os.path.exists(wipe_base_folder):
      return
    wipe_wrapper_list = [f for f in os.listdir(wipe_base_folder)
                         if os.path.isfile(os.path.join(wipe_base_folder, f))]
    if len(wipe_wrapper_list) > 0:
      group_name = partition.partition_id + '-' + "destroy"
      logger.info("Adding pre-destroy scripts to supervisord...")
      partition.generateSupervisorConfiguration()
      partition.addServiceToCustomGroup(group_name,
                                        wipe_wrapper_list,
                                        wipe_base_folder)
  
      partition.writeSupervisorConfigurationFile()

      # check the state of all process, if the process is not started yes, start it
      supervisord = partition.getSupervisorRPC()
      process_list_string = ""
      for name in wipe_wrapper_list:
        process_name = group_name + ':' + name
        process_list_string += process_name + '\n'
        status = supervisord.getProcessInfo(process_name)
        if status['start'] == 0:
          # process is not started yet
          logger.info("Starting pre-destroy process %r..." % name)
          supervisord.startProcess(process_name, False)

      # ask to slapgrid to check theses scripts before destroy partition
      with open(wait_filepath, 'w') as f:
        f.write(process_list_string)
