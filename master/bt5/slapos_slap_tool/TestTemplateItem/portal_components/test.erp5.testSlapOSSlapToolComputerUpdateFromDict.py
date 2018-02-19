# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from erp5.component.test.SlapOSTestCaseMixin import SlapOSTestCaseMixinWithAbort

class TestSlapOSCoreComputerUpdateFromDict(SlapOSTestCaseMixinWithAbort):

  def afterSetUp(self):
    SlapOSTestCaseMixinWithAbort.afterSetUp(self)
    self.computer = self.portal.computer_module.template_computer\
        .Base_createCloneDocument(batch_mode=1)
    self.computer.edit(
      reference='TESTC-%s' % self.generateNewId(),
    )

    # All tests expect no address in the default computer
    address_list = self.computer.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)

    # All tests expect no partition in the default computer
    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 0)

  #############################################
  # Computer network information
  #############################################
  def test_CreateComputerNetworkInformation(self):
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    self.assertEqual(self.computer.getQuantity(), 0)
    address_list = self.computer.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'a')
    self.assertEqual(address.getNetmask(), 'b')
    self.assertEqual(address.getId(), 'default_network_address')

  def test_UpdateComputerNetworkInformation(self):
    self.computer.newContent(
      id='foo',
      portal_type='Internet Protocol Address',
      )

    parameter_dict = {
      'partition_list': [],
      'address': 'c',
      'netmask': 'd',
    }
    self.computer.Computer_updateFromDict(parameter_dict)
    self.assertEqual(self.computer.getQuantity(), 0)
    address_list = self.computer.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    # Existing document should be edited if possible
    self.assertEqual(address.getId(), 'foo')

  def test_RemoveComputerNetworkInformation(self):
    self.computer.newContent(
      id='foo',
      portal_type='Internet Protocol Address',
      )
    self.computer.newContent(
      id='bar',
      portal_type='Internet Protocol Address',
      )

    parameter_dict = {
      'partition_list': [],
      'address': 'e',
      'netmask': 'f',
    }
    self.computer.Computer_updateFromDict(parameter_dict)
    self.assertEqual(self.computer.getQuantity(), 0)
    # One address should be removed
    address_list = self.computer.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'e')
    self.assertEqual(address.getNetmask(), 'f')
    # Existing document should be edited if possible
    self.assertTrue(address.getId() in ('foo', 'bar'))

  #############################################
  # Computer Partition network information
  #############################################
  def test_CreateSinglePartitionNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    self.assertEqual(address.getNetworkInterface(), 'bar')
    self.assertEqual(address.getId(), 'default_network_address')
  
  def test_CreateSinglePartition_TapNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar',
                'ipv4_addr': 'e',
                'ipv4_netmask': 'f',
                'ipv4_network': 'g',
                'ipv4_gateway': 'h'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 2)
    address_list.sort(key=lambda x: {0: 1, 1: 2}[int(x.getId() != 'default_network_address')])
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    self.assertEqual(address.getNetworkInterface(), 'bar')
    self.assertEqual(address.getId(), 'default_network_address')
    
    address1 = address_list[1]
    self.assertEqual(address1.getIpAddress(), 'e')
    self.assertEqual(address1.getNetmask(), 'f')
    self.assertEqual(address1.getNetworkAddress(), 'g')
    self.assertEqual(address1.getGatewayIpAddress(), 'h')
    self.assertEqual(address1.getNetworkInterface(), 'route_bar')

  def test_CreateMultiplePartitionNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
          },{
          'addr': 'e',
          'netmask': 'f',
        }],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 2)
    default_address = [x for x in address_list \
        if x.getId() == 'default_network_address'][0]
    self.assertEqual(default_address.getIpAddress(), 'c')
    self.assertEqual(default_address.getNetmask(), 'd')
    self.assertEqual(default_address.getNetworkInterface(), 'bar')

    other_address = [x for x in address_list \
        if x.getId() != 'default_network_address'][0]
    self.assertEqual(other_address.getIpAddress(), 'e')
    self.assertEqual(other_address.getNetmask(), 'f')
    self.assertEqual(other_address.getNetworkInterface(), 'bar')

  def test_CreateMultiplePartition_TapNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
          },{
          'addr': 'e',
          'netmask': 'f',
        }],
        'tap': {'name': 'bar',
                'ipv4_addr': 'g',
                'ipv4_netmask': 'h',
                'ipv4_network': 'i',
                'ipv4_gateway': 'j'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 3)
    default_address = [x for x in address_list \
        if x.getId() == 'default_network_address'][0]
    self.assertEqual(default_address.getIpAddress(), 'c')
    self.assertEqual(default_address.getNetmask(), 'd')
    self.assertEqual(default_address.getNetworkInterface(), 'bar')

    other_address_list = [x for x in address_list \
        if x.getId() != 'default_network_address']
    other_address_list.sort(key=lambda x: {1: 1, 0: 2}[int(x.getNetworkInterface() == 'bar')])
    other_address = other_address_list[0]
    self.assertEqual(other_address.getIpAddress(), 'e')
    self.assertEqual(other_address.getNetmask(), 'f')
    self.assertEqual(other_address.getNetworkInterface(), 'bar')
    
    other_address1 = other_address_list[1]
    self.assertEqual(other_address1.getIpAddress(), 'g')
    self.assertEqual(other_address1.getNetmask(), 'h')
    self.assertEqual(other_address1.getNetworkAddress(), 'i')
    self.assertEqual(other_address1.getGatewayIpAddress(), 'j')
    self.assertEqual(other_address1.getNetworkInterface(), 'route_bar')

  def test_UpdateSinglePartitionNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    address = partition.newContent(
      id ='foo',
      portal_type='Internet Protocol Address',
    )

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    self.assertEqual(address.getNetworkInterface(), 'bar')
    self.assertEqual(address.getId(), 'foo')

  def test_UpdateSinglePartition_TapNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    address = partition.newContent(
      id ='foo',
      portal_type='Internet Protocol Address',
    )

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar',
                'ipv4_addr': 'e',
                'ipv4_netmask': 'f',
                'ipv4_network': 'g',
                'ipv4_gateway': 'h'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 2)
    address_list.sort(key=lambda x: {1: 1, 0: 2}[int(x.getNetworkInterface() == 'bar')])
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    self.assertEqual(address.getNetworkInterface(), 'bar')
    self.assertEqual(address.getId(), 'foo')
    
    other_address = address_list[1]
    self.assertEqual(other_address.getIpAddress(), 'e')
    self.assertEqual(other_address.getNetmask(), 'f')
    self.assertEqual(other_address.getNetworkAddress(), 'g')
    self.assertEqual(other_address.getGatewayIpAddress(), 'h')
    self.assertEqual(other_address.getNetworkInterface(), 'route_bar')

  def test_UpdateMultiplePartitionNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    other_address = partition.newContent(
      id ='foo',
      portal_type='Internet Protocol Address',
    )
    default_address = partition.newContent(
      id ='default_network_interface',
      portal_type='Internet Protocol Address',
    )

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
          },{
          'addr': 'e',
          'netmask': 'f',
        }],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 2)

    # First address should go to the default one
    self.assertEqual(default_address.getIpAddress(), 'c')
    self.assertEqual(default_address.getNetmask(), 'd')
    self.assertEqual(default_address.getNetworkInterface(), 'bar')

    self.assertEqual(other_address.getIpAddress(), 'e')
    self.assertEqual(other_address.getNetmask(), 'f')
    self.assertEqual(other_address.getNetworkInterface(), 'bar')

  def test_UpdateMultiplePartition_TapNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    other_address = partition.newContent(
      id ='foo',
      portal_type='Internet Protocol Address',
    )
    partition.newContent(
      id ='route_foo',
      portal_type='Internet Protocol Address',
    )
    default_address = partition.newContent(
      id ='default_network_interface',
      portal_type='Internet Protocol Address',
    )

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
          },{
          'addr': 'e',
          'netmask': 'f',
        }],
        'tap': {'name': 'bar',
                'ipv4_addr': 'g',
                'ipv4_netmask': 'h',
                'ipv4_network': 'i',
                'ipv4_gateway': 'j'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 3)

    # First address should go to the default one
    self.assertEqual(default_address.getIpAddress(), 'c')
    self.assertEqual(default_address.getNetmask(), 'd')
    self.assertEqual(default_address.getNetworkInterface(), 'bar')

    other_address_list = [x for x in address_list \
        if x.getId() != 'default_network_interface']
    other_address_list.sort(
          key=lambda x: {1: 1, 0: 2}[int(x.getNetworkInterface() == 'bar')])
    other_address = other_address_list[0]
    self.assertEqual(other_address.getIpAddress(), 'e')
    self.assertEqual(other_address.getNetmask(), 'f')
    self.assertEqual(other_address.getNetworkInterface(), 'bar')
    
    other_address = other_address_list[1]
    self.assertEqual(other_address.getIpAddress(), 'g')
    self.assertEqual(other_address.getNetmask(), 'h')
    self.assertEqual(other_address.getNetworkAddress(), 'i')
    self.assertEqual(other_address.getGatewayIpAddress(), 'j')
    self.assertEqual(other_address.getNetworkInterface(), 'route_bar')

  def test_removePartitionTapNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar',
                'ipv4_addr': 'e',
                'ipv4_netmask': 'f',
                'ipv4_network': 'g',
                'ipv4_gateway': 'h'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    parameter_dict2 = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    
    self.computer.Computer_updateFromDict(parameter_dict)
    
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    address_list.sort(
      key=lambda x: {1: 1, 0: 2}[int(x.getId() == 'default_network_address')])
    self.assertEqual(len(address_list), 2)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    self.assertEqual(address.getNetworkInterface(), 'bar')
    self.assertEqual(address.getId(), 'default_network_address')
    
    other_address = address_list[1]
    self.assertEqual(other_address.getIpAddress(), 'e')
    self.assertEqual(other_address.getNetmask(), 'f')
    self.assertEqual(other_address.getNetworkAddress(), 'g')
    self.assertEqual(other_address.getGatewayIpAddress(), 'h')
    self.assertEqual(other_address.getNetworkInterface(), 'route_bar')
    
    self.computer.Computer_updateFromDict(parameter_dict2)
    
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    self.assertEqual(address_list[0].getIpAddress(), 'c')
    self.assertEqual(address_list[0].getNetmask(), 'd')
    self.assertEqual(address_list[0].getNetworkInterface(), 'bar')
    self.assertEqual(address_list[0].getId(), 'default_network_address')

  def test_RemoveSinglePartitionNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    partition.newContent(
      id ='foo',
      portal_type='Internet Protocol Address',
    )
    partition.newContent(
      id ='default_network_interface',
      portal_type='Internet Protocol Address',
    )

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [{
          'addr': 'c',
          'netmask': 'd',
        }],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 1)
    address = address_list[0]
    self.assertEqual(address.getIpAddress(), 'c')
    self.assertEqual(address.getNetmask(), 'd')
    self.assertEqual(address.getNetworkInterface(), 'bar')
    self.assertEqual(address.getId(), 'default_network_interface')

  def test_RemoveMultiplePartitionNetworkInformation(self):
    partition = self.computer.newContent(
      reference='foo',
      portal_type='Computer Partition',
    )
    # No address in the empty partition
    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)
    partition.newContent(
      id ='foo',
      portal_type='Internet Protocol Address',
    )
    partition.newContent(
      id ='default_network_interface',
      portal_type='Internet Protocol Address',
    )

    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    address_list = partition.contentValues(
        portal_type='Internet Protocol Address')
    self.assertEqual(len(address_list), 0)

  #############################################
  # Computer Partition information
  #############################################
  def test_CreateSinglePartition(self):
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')

  def test_CreateMultiplePartition(self):
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo1',
        'address_list': [],
        'tap': {'name': 'bar1'},
      },{
        'reference': 'foo2',
        'address_list': [],
        'tap': {'name': 'bar2'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 2)

    partition = [x for x in partition_list \
        if x.getReference() == 'foo1'][0]
    self.assertEqual(partition.getReference(), 'foo1')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')

    partition = [x for x in partition_list \
        if x.getReference() != 'foo1'][0]
    self.assertEqual(partition.getReference(), 'foo2')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')

  # Code does not enter in such state (yet?)
#   def test_UpdateDraftSinglePartition(self):
#     partition = self.computer.newContent(
#       id='bar',
#       reference='foo',
#       portal_type='Computer Partition',
#     )
#     parameter_dict = {
#       'partition_list': [{
#         'reference': 'foo',
#         'address_list': [],
#         'tap': {'name': 'bar'},
#       }],
#       'address': 'a',
#       'netmask': 'b',
#     }
#     self.computer.Computer_updateFromDict(parameter_dict)
# 
#     partition_list = self.computer.contentValues(
#         portal_type='Computer Partition')
#     self.assertEqual(len(partition_list), 1)
#     partition = partition_list[0]
#     self.assertEqual(partition.getReference(), 'foo')
#     self.assertEqual(partition.getValidationState(), 'validated')
#     self.assertEqual(partition.getSlapState(), 'free')
#     self.assertEqual(partition.getId(), 'bar')

  def test_UpdateInvalidatedSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.validate()
    partition.invalidate()
    partition.markFree()
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')
    self.assertEqual(partition.getId(), 'bar')

  def test_UpdateValidatedSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.validate()
    partition.markFree()
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')
    self.assertEqual(partition.getId(), 'bar')

  def test_UpdateFreeSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.markFree()
    partition.validate()
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')
    self.assertEqual(partition.getId(), 'bar')

  def test_UpdateBusySinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.markFree()
    partition.markBusy()
    partition.validate()
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'busy')
    self.assertEqual(partition.getId(), 'bar')

  def test_UpdateInactiveSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.markInactive()
    partition.validate()
    parameter_dict = {
      'partition_list': [{
        'reference': 'foo',
        'address_list': [],
        'tap': {'name': 'bar'},
      }],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'validated')
    self.assertEqual(partition.getSlapState(), 'free')
    self.assertEqual(partition.getId(), 'bar')

  def test_RemoveDraftSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'draft')
    self.assertEqual(partition.getSlapState(), 'draft')
    self.assertEqual(partition.getId(), 'bar')

  def test_RemoveInvalidatedSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.validate()
    partition.invalidate()
    partition.markFree()
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'invalidated')
    self.assertEqual(partition.getSlapState(), 'inactive')
    self.assertEqual(partition.getId(), 'bar')

  def test_RemoveValidatedSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.validate()
    partition.markFree()
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'invalidated')
    self.assertEqual(partition.getSlapState(), 'inactive')
    self.assertEqual(partition.getId(), 'bar')

  def test_RemoveFreeSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.markFree()
    partition.validate()
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'invalidated')
    self.assertEqual(partition.getSlapState(), 'inactive')
    self.assertEqual(partition.getId(), 'bar')

  def test_RemoveBusySinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.markFree()
    partition.markBusy()
    partition.validate()
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'invalidated')
    self.assertEqual(partition.getSlapState(), 'busy')
    self.assertEqual(partition.getId(), 'bar')

  def test_RemoveInactiveSinglePartition(self):
    partition = self.computer.newContent(
      id='bar',
      reference='foo',
      portal_type='Computer Partition',
    )
    partition.markInactive()
    partition.validate()
    parameter_dict = {
      'partition_list': [],
      'address': 'a',
      'netmask': 'b',
    }
    self.computer.Computer_updateFromDict(parameter_dict)

    partition_list = self.computer.contentValues(
        portal_type='Computer Partition')
    self.assertEqual(len(partition_list), 1)
    partition = partition_list[0]
    self.assertEqual(partition.getReference(), 'foo')
    self.assertEqual(partition.getValidationState(), 'invalidated')
    self.assertEqual(partition.getSlapState(), 'inactive')
    self.assertEqual(partition.getId(), 'bar')













#   def test_Computer_checkAndUpdateCapacityScope_no_capacity_quantity(self):
#     self._makeTree()
#     self.computer.edit(capacity_quantity=1)
#     partition = self.computer.newContent(portal_type='Computer Partition',
#         reference='part1')
#     partition.markFree()
#     partition.markBusy()
#     partition.validate()
#     self.software_instance.setAggregate(partition.getRelativeUrl())
#     self.tic()
# 
#     self.computer.Computer_checkAndUpdateCapacityScope()
#     self.assertEqual('close', self.computer.getCapacityScope())
#     self.assertEqual('Computer capacity limit exceeded',
#         self.computer.workflow_history['edit_workflow'][-1]['comment'])
# 
#   def test_Computer_checkAndUpdateCapacityScope_no_access(self):
#     self.computer.edit(reference='TESTC-%s' % self.generateNewId())
#     self.computer.Computer_checkAndUpdateCapacityScope()
#     self.assertEqual('close', self.computer.getCapacityScope())
#     self.assertEqual("Computer didn't contact the server",
#         self.computer.workflow_history['edit_workflow'][-1]['comment'])
# 
#   def test_Computer_checkAndUpdateCapacityScope_close(self):
#     self.computer.edit(capacity_scope='close')
#     self.computer.Computer_checkAndUpdateCapacityScope()
#     self.assertEqual('open', self.computer.getCapacityScope())
# 
#   def test_Computer_checkAndUpdateCapacityScope_with_error(self):
#     memcached_dict = self.portal.portal_memcached.getMemcachedDict(
#         key_prefix='slap_tool',
#         plugin_path='portal_memcached/default_memcached_plugin')
#     memcached_dict[self.computer.getReference()] = json.dumps({
#         'text': '#error not ok'
#     })
#     self.computer.Computer_checkAndUpdateCapacityScope()
#     self.assertEqual('close', self.computer.getCapacityScope())
#     self.assertEqual("Computer reported an error",
#         self.computer.workflow_history['edit_workflow'][-1]['comment'])
# 
#   def test_Computer_checkAndUpdateCapacityScope_with_error_non_public(self):
#     memcached_dict = self.portal.portal_memcached.getMemcachedDict(
#         key_prefix='slap_tool',
#         plugin_path='portal_memcached/default_memcached_plugin')
#     memcached_dict[self.computer.getReference()] = json.dumps({
#         'text': '#error not ok'
#     })
#     self.computer.edit(allocation_scope='open/personal')
#     self.computer.Computer_checkAndUpdateCapacityScope()
#     self.assertEqual('open', self.computer.getCapacityScope())
# 
#   def _simulateComputer_checkAndUpdateCapacityScope(self):
#     script_name = 'Computer_checkAndUpdateCapacityScope'
#     if script_name in self.portal.portal_skins.custom.objectIds():
#       raise ValueError('Precondition failed: %s exists in custom' % script_name)
#     createZODBPythonScript(self.portal.portal_skins.custom,
#                         script_name,
#                         '*args, **kwargs',
#                         '# Script body\n'
# """portal_workflow = context.portal_workflow
# portal_workflow.doActionFor(context, action='edit_action', comment='Visited by Computer_checkAndUpdateCapacityScope') """ )
#     transaction.commit()
# 
#   def _dropComputer_checkAndUpdateCapacityScope(self):
#     script_name = 'Computer_checkAndUpdateCapacityScope'
#     if script_name in self.portal.portal_skins.custom.objectIds():
#       self.portal.portal_skins.custom.manage_delObjects(script_name)
#     transaction.commit()
# 
#   def test_alarm(self):
#     self._simulateComputer_checkAndUpdateCapacityScope()
#     try:
#       self.portal.portal_alarms.slapos_update_computer_capacity_scope.activeSense()
#       self.tic()
#     finally:
#       self._dropComputer_checkAndUpdateCapacityScope()
#     self.assertEqual(
#         'Visited by Computer_checkAndUpdateCapacityScope',
#         self.computer.workflow_history['edit_workflow'][-1]['comment'])
# 
#   def test_alarm_non_public(self):
#     self.computer.edit(allocation_scope='open/personal')
#     self.tic()
#     self._simulateComputer_checkAndUpdateCapacityScope()
#     try:
#       self.portal.portal_alarms.slapos_update_computer_capacity_scope.activeSense()
#       self.tic()
#     finally:
#       self._dropComputer_checkAndUpdateCapacityScope()
#     self.assertNotEqual(
#         'Visited by Computer_checkAndUpdateCapacityScope',
#         self.computer.workflow_history['edit_workflow'][-1]['comment'])
# 
#   def test_alarm_invalidated(self):
#     self.computer.invalidate()
#     self.tic()
#     self._simulateComputer_checkAndUpdateCapacityScope()
#     try:
#       self.portal.portal_alarms.slapos_update_computer_capacity_scope.activeSense()
#       self.tic()
#     finally:
#       self._dropComputer_checkAndUpdateCapacityScope()
#     self.assertNotEqual(
#         'Visited by Computer_checkAndUpdateCapacityScope',
#         self.computer.workflow_history['edit_workflow'][-1]['comment'])
