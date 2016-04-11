"""
  Make a list with delta CO2 values
"""

if simulated_cpu_load is not None:
  partition_average_cpu_load = simulated_cpu_load
else:
  partition_average_cpu_load = context.getCpuCapacityQuantity()

partition_delta_co2_dict = {} 

for computer_partition in computer_partition_list:
  computer = computer_partition.getParentValue()
  computer_zero_emission_ratio = computer.Computer_getZeroEmissionRatio()
  computer_cpu_load_percentage = computer.Computer_getLatestCPUPercentLoad()
  computer_watt = computer.Computer_getWattConsumption(computer_cpu_load_percentage)

  partition_watt = computer.Computer_getWattConsumption(
                computer_cpu_load_percentage + partition_average_cpu_load)

  delta_watt = (partition_watt-computer_watt)

  delta_co2 = delta_watt - delta_watt*(computer_zero_emission_ratio/100)

  if delta_co2 in partition_delta_co2_dict:
    partition_delta_co2_dict[delta_co2].append(computer_partition)
  else:
    partition_delta_co2_dict[delta_co2] = [computer_partition]

return partition_delta_co2_dict
