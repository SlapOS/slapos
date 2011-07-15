from slapos.recipe.librecipe import BaseSlapRecipe
import os
import sys
import zc.buildout
import zc.recipe.egg
from slapos.slap.slap import ServerError
from slapos.tool.cloudmgr.cloudinterface import NodeInterface
from pprint import pformat
class SlavePartitionError(Exception):
  pass

class Recipe(BaseSlapRecipe):
  SECURITY_GROUP_NAME = 'VifibEC2Security'
  def __init__(self, buildout, name, options):
    BaseSlapRecipe.__init__(self, buildout, name, options)
    self.destroy_wrapper_location = os.path.join(self.bin_directory, 'destroy')
    self.running_wrapper_location = os.path.join(self.bin_directory, 'run')

    # wrapper parts
    options['scripts'] = '''
      run
      destroy
    '''
    options['entry-points'] = '''
      run=slapos.recipe.libcloud.run:run
      destroy=slapos.recipe.libcloud.destroy:destroy
    '''
    self.egg = zc.recipe.egg.Egg(buildout, '', options)

    self.configuration_file = os.path.join(self.etc_directory, 'cloudmgr.cnf')

  def _loadSecretAndKey(self):
    """Loads security parameters for connection"""
    self.secret = open(os.path.join(self.work_directory, 'secret.txt')
        ).read().strip()
    self.key = open(os.path.join(self.work_directory, 'key.txt')
        ).read().strip()

  def _updateConfigurationFile(self):
    configuration_dict = dict(
      key=self.key,
      secret=self.secret,
      node_list=self.slave_partition_configuration_dict_list
    )
    self._writeFile(self.configuration_file, pformat(configuration_dict))

  def _install(self):
    """libcloud compatible machine is installed by creating wrapper, which
    will run succesfully as long as the machine is available.
    """
    self._loadSecretAndKey()
    self.slave_partition_configuration_dict_list = []
    self.egg.extra_paths = sys.path
    for slave_partition in [self.slap.registerComputerPartition(
      self.computer_id, slave_id) for slave_id in self.computer_partition\
          .getInstanceParameterDict()['slave_id_list']]:
      try:
        self.slave_partition_configuration_dict_list.append(
            self._installSlavePartition(slave_partition))
      except SlavePartitionError, e:
        self.logger.warning('Slave Parttion %r not installed, issue: %r'%(
          slave_partition.getId(), e))
    # Installs wrappers
    self._updateConfigurationFile()
    self.options['arguments'] = "server_binary = %r, configuration_file = %r"%(
        self.options['server_binary'], self.configuration_file)
    self.egg.install()
    os.chmod(os.path.join(
      self.running_wrapper_location), int('0700', 8))
    os.chmod(os.path.join(
      self.destroy_wrapper_location), int('0700', 8))
    return []

  def _installSlavePartition(self, slave_partition):
    requested_dict = slave_partition.getInstanceParameterDict()
    requested_dict.setdefault('service', 'EC2_EU_WEST')
    requested_dict.setdefault('location', '0')
    requested_dict.setdefault('image', 'ami-05cae171')
    requested_dict.setdefault('size', 'm1.smal')
    requested_dict.setdefault('security_group', 'VifibEC2Security')
    connection_dict = slave_partition.getConnectionDict()
    node_kw = dict(
      key = self.key,
      secret = self.secret,
      service = requested_dict['service'],
      location = requested_dict['location'],
      node_uuid = connection_dict.get('node_uuid', None),
      ssh_key = connection_dict.get('ssh_key', None)
    )
    node = NodeInterface(**node_kw)
    update_kw = dict(
      image = requested_dict['image'],
      size = requested_dict['size'],
      security_group = requested_dict['security_group'],
    )
    self.logger.info('Updating %r' % slave_partition.getId())
    connection_dict.update(node.update(**update_kw))
    self.logger.info('Fetching public ip of %r' % slave_partition.getId())
    connection_dict.update(node.getPublicIpList())
    slave_partition.available()
    connection_dict.setdefault('username', 'root')
    slave_partition.setConnectionDict(connection_dict)
    requested_dict.update(connection_dict)
    slave_partition_state = slave_partition.getState()
    # as cloudmgr is not related with slap and runs as async process to recipe
    # assume that whatever came from slave is correctly done
    if slave_partition_state in ['started', 'stopped']:
      # stopped cannot be supported, because in case of libcloud it is equal
      # to destroyed
      # even worse: stopped is the first state for installed partition
      try:
        getattr(slave_partition, slave_partition_state)()
      except ServerError:
        # Recipe is becoming responsible for system state, so it have to
        # not die in case of slap server error
        pass
      requested_dict['requested_state'] = 'started'
    elif slave_partition_state == 'destroyed':
      requested_dict['requested_state'] = slave_partition_state
      try:
        slave_partition.destroyed()
      except ServerError:
        # Recipe is becoming responsible for system state, so it have to
        # not die in case of slap server error
        pass
    return requested_dict

