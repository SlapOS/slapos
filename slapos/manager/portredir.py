# coding: utf-8
import json
import logging
import netaddr
import os

from .interface import IManager
from itertools import ifilter
from zope import interface

logger = logging.getLogger(__name__)

def _format_ip_addr(ip_addr):
  if ip_addr.version == 6:
    return '[{}]'.format(ip_addr)
  return str(ip_addr)

def which(exename):
  for path in os.environ["PATH"].split(os.pathsep):
    full_path = os.path.join(path, exename)
    if os.path.exists(full_path):
      return full_path
  return None

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
      try:
        port_redirects = json.load(f)
      except:
        logger.warning('Bad port redirection config file', exc_info=True)
        return

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
      redir_type = port_redirect.get('type', 'tcp')
      if redir_type.lower() not in {'tcp', 'udp'}:
        logger.warning('Bad source redirection type: %s', redir_type)
        continue

      try:
        source_port = int(port_redirect['srcPort'])
      except:
        logger.warning('Bad source port provided', exc_info=True)
        continue

      try:
        source_addr = port_redirect.get('srcAddress')
        if source_addr is not None:
          source_addr = netaddr.IPAddress(source_addr)
      except:
        logger.warning('Bad source address provided', exc_info=True)
        continue

      try:
        dest_port = int(port_redirect['destPort'])
      except:
        logger.warning('Bad source port provided', exc_info=True)
        continue

      try:
        dest_addr = port_redirect.get('destAddress', partition_ipv6)
        dest_addr = netaddr.IPAddress(dest_addr)
      except:
        logger.warning('Bad source address provided', exc_info=True)
        continue

      command = [which('socat')]

      socat_source_version = source_addr.version if source_addr is not None else 4
      socat_source_type = '{rtype}{version}-LISTEN'.format(rtype=redir_type.upper(), version=socat_source_version)
      socat_source = '{}:{}'.format(socat_source_type, source_port)
      if source_addr is not None:
        socat_source += ',bind={}'.format(source_addr)
      socat_source += ',fork'
      command.append(socat_source)

      socat_dest_type = '{rtype}{version}'.format(rtype=redir_type.upper(), version=dest_addr.version)
      socat_dest = '{}:{}:{}'.format(socat_dest_type, _format_ip_addr(dest_addr), dest_port)
      command.append(socat_dest)

      # If source port >= 1024, we don't need to run as root
      as_user = source_port >= 1024

      socat_programs.append({
        'as_user': as_user,
        'command': ' '.join(command),
        'name': 'socat-{}-{}'.format(redir_type.lower(), source_port),
      })

    # Generate supervisord configuration with socat processes added
    partition.generateSupervisorConfiguration()

    group_id = partition.addCustomGroup('socat', partition.partition_id,
                                        [program['name']
                                         for program in socat_programs])
    for program in socat_programs:
      partition.addProgramToGroup(group_id, program['name'], program['name'],
                                  program['command'],
                                  as_user=program['as_user'])

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
