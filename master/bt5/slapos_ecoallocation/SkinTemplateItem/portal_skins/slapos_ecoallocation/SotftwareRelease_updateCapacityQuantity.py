"""
"""
edit_kw = {}
average_cpu_load = context.SoftwareRelease_getAverageConsumedCPULoad()
average_memory_usage = context.SoftwareRelease_getAverageConsumedMemory()


if average_cpu_load != context.getCpuCapacityQuantity():
  edit_kw["cpu_capacity_quantity"] = average_cpu_load

if average_memory_usage != context.getMemoryCapacityQuantity(): 
  edit_kw["memory_capacity_quantity"] = average_memory_usage
  
if len(edit_kw) > 0:
  context.edit(**edit_kw)
