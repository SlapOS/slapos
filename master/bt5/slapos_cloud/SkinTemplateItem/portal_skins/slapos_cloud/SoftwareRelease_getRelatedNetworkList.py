network_list = []
for computer in context.SoftwareRelease_getUsableComputerList():
  network = computer.getSubordinationValue()
  if network and not network in network_list:
    network_list.append(network)

return network_list
