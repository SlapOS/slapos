partition_co2_dict = {}
min_delta_co2 = 2000
minimal_candidate = None

for software_instance in context.getSpecialiseRelatedValueList(portal_type="Software Instance"):
  delta_co2 = software_instance.SoftwareInstance_getFutureDeltaCO2()     
  if delta_co2 != "Not Applicable":
    if delta_co2 < min_delta_co2:
      minimal_candidate = software_instance
      min_delta_co2 = delta_co2
    elif (delta_co2 == min_delta_co2) and \
           (software_instance.getTitle() in ["kvm0", "runner0"]):
      minimal_candidate = software_instance

return minimal_candidate, min_delta_co2
