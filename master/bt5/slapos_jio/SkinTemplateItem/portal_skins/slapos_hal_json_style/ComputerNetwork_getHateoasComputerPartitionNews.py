if REQUEST is not None:
  raise Unauthorized

computer_network_partition_dict = {}
for computer in context.getSubordinationRelatedValueList(portal_type="Computer"):
  computer_network_partition_dict[computer.getReference()] = computer.Computer_getHateoasComputerPartitionNews()

return computer_network_partition_dict
