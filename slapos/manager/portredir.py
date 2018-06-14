# coding: utf-8
import json
import logging
import os.path

from .interface import IManager
from itertools import ifilter
from zope import interface

logger = logging.getLogger(__name__)

class Manager(object):
  interface.implements(IManager)

  port_redirect_filename = '.slapos-port-redirect'

  def __init__(self, config):
    """Manager needs to know config for its functioning.
    """
    self.config = config

  def format(self, computer):
    """Method called at `slapos node format` phase.

    :param computer: slapos.format.Computer, currently formatted computer
    """

  def formatTearDown(self, computer):
    """Method called after `slapos node format` phase.

    :param computer: slapos.format.Computer, formatted computer
    """

  def software(self, software):
    """Method called at `slapos node software` phase.

    :param software: slapos.grid.SlapObject.Software, currently processed software
    """

  def softwareTearDown(self, software):
    """Method called after `slapos node software` phase.

    :param computer: slapos.grid.SlapObject.Software, processed software
    """

  def instance(self, partition):
    """Method called at `slapos node instance` phase.

    :param partition: slapos.grid.SlapObject.Partition, currently processed partition
    """

  def instanceTearDown(self, partition):
    """Method  called after `slapos node instance` phase.

    :param partition: slapos.grid.SlapObject.Partition, processed partition
    """
    # Test presence of port redirection file
    port_redirect_file_path = os.path.join(partition.instance_path, self.port_redirect_filename)
    if not os.path.exists(port_redirect_file_path):
      return

    # Read it
    with open(port_redirect_file_path) as f:
      port_redirects = json.load(f)

    # Get partitions IPv6 address
    computer_partition = partition.computer_partition
    parameter_dict = computer_partition.getInstanceParameterDict()

    partition_ip_list = parameter_dict['ip_list'] + parameter_dict.get(
      'full_ip_list', [])
    partition_ip_list = [tup[1] for tup in partition_ip_list]

    partition_ipv6 = next(ifilter(lambda ip_addr: ':' in ip_addr,
                                 partition_ip_list),
                          None)

    # Generate socat commands to run with supervisord
    socat_programs = []
    for port_redirect in port_redirects:
      source_port = port_redirect['srcPort']
      source_addr = port_redirect.get('srcAddress')

      source_is_ipv4 = source_addr is None or '.' in source_addr

      dest_port = port_redirect['destPort']
      dest_addr = port_redirect.get('destAddress', partition_ipv6)

      dest_is_ipv6 = ':' in dest_addr
      if dest_is_ipv6:
        dest_addr = '[{}]'.format(dest_addr)

      command = ['socat']

      socat_source_type = 'TCP4-LISTEN' if source_is_ipv4 else 'TCP6-LISTEN'
      socat_source = '{}:{}'.format(socat_source_type, source_port)
      if source_addr is not None:
        socat_source += ',bind={}'.format(source_addr)
      socat_source += ',fork'
      command.append(socat_source)

      socat_dest_type = 'TCP6' if dest_is_ipv6 else 'TCP4'
      socat_dest = '{}:{}:{}'.format(socat_dest_type, dest_addr, dest_port)
      command.append(socat_dest)

      socat_programs.append({
        'command': ' '.join(command),
        'name': 'socat-{}'.format(source_port),
      })

    # Generate supervisord configuration with socat processes added
    partition.generateSupervisorConfiguration()

    group_id = partition.addCustomGroup('socat', partition.partition_id,
                                        [program['name']
                                         for program in socat_programs])
    for program in socat_programs:
      partition.addProgramToGroup(group_id, program['name'], program['name'],
                                  program['command'], as_user=False)

    partition.writeSupervisorConfigurationFile()

    # Start processes
    supervisord = partition.getSupervisorRPC()
    for program in socat_programs:
      process_name = '{}:{}'.format(group_id, program['name'])
      status = supervisord.getProcessInfo(process_name)

      if status['start'] == 0:
        supervisord.startProcess(process_name, False)

  def report(self, partition):
    """Method called at `slapos node report` phase.

    :param partition: slapos.grid.SlapObject.Partition, currently processed partition
    """
