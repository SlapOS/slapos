if REQUEST is not None:
  raise Unauthorized("Unauthorized call script from URL")

model_id = context.getWattConsumptionModel("no_model")

######
# Introduce your Consumption Model here
######
def consumption_model_shuttle_ds61_i7(load):
  """ Expected consumed watts for the computer load
  """
  if load <= 25:
   return 21.5 + 1.06*load
  else:
   return 48 + 0.29*load

def consumption_model_shuttle_nuc_i7(load):
  """ Expected consumed watts for the computer load
  """
  if load <= 25:
   return 8.5 + 0.46*load
  else:
   return 20 + 0.08*load

def consumption_model_rikomagic_mk802iv(load):
  """ Expected consumed watts for the computer load
  """
  if load <= 25:
   return 2.2 + 0.04*load
  else:
   return 3.2 + 0.008*load

def no_model(load):
  return 0

model_map = {
  "shuttle_ds61_i7" : consumption_model_shuttle_ds61_i7,
  "rikomagic_mk802iv": consumption_model_rikomagic_mk802iv,
  "intel_nuc_i7": consumption_model_shuttle_nuc_i7
}
if cpu_load_percentage is None:
  cpu_load_percentage = context.Computer_getLatestCPUPercentLoad()

cpu_load_percentage += partition_increment

return model_map.get(model_id, no_model)(cpu_load_percentage)
