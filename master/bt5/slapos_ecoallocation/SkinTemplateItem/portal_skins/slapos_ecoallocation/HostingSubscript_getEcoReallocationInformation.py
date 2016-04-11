instance, delta_co2 = context.HostingSubscription_getMostEcoEfficientSoftwareInstance()

if instance is None:
  return None 

master_node = instance.SoftwareInstance_getResilientMasterNode()

if master_node is None:
  return None 

if instance.getRelativeUrl() != master_node.getRelativeUrl():
  master_delta_co2 = master_node.SoftwareInstance_getFutureDeltaCO2()
  saving_ratio = (master_delta_co2-delta_co2)/master_delta_co2
  return "Improve Power efficiency in %s%% by using %s instance as Main Node. We recommend you to a take over." % (int(saving_ratio*100), instance.getTitle())


return None
