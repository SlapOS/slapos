instance = state_change['object']
portal = instance.getPortalObject()
# Get required arguments
kwargs = state_change.kwargs

# Required args
# Raise TypeError if all parameters are not provided
try:
  software_release_url_string = state_change.kwargs['software_release']
  software_type = kwargs["software_type"]
  instance_xml = kwargs["instance_xml"]
  sla_xml = kwargs["sla_xml"]
  is_slave = kwargs["shared"]
except KeyError:
  raise TypeError, "RequestedInstance_updateParameterInformation takes exactly 5 arguments"

edit_kw = {
  'url_string': software_release_url_string,
  'text_content': instance_xml,
  'source_reference': software_type,
  'sla_xml': sla_xml,
}

# Check the slave management
if is_slave not in [True, False]:
  raise ValueError, "shared should be a boolean"
instance_portal_type = instance.getPortalType()
if instance_portal_type == "Hosting Subscription":
  edit_kw['root_slave'] = is_slave
elif instance_portal_type == "Software Instance":
  if is_slave:
    raise NotImplementedError, "Please destroy before doing a slave instance (%s)" % \
      (instance.getRelativeUrl(), )
elif instance_portal_type == "Slave Instance":
  if not is_slave:
    raise NotImplementedError, "Please destroy before doing a software instance (%s)" % \
      (instance.getRelativeUrl(), )
else:
  raise NotImplementedError, "Not supported portal type %s (%s)" % \
    (instance.getPortalType(), instance.getRelativeUrl())

instance.edit(**edit_kw)
# Prevent storing broken XML in text content (which prevent to update parameters after)
context.Instance_checkConsistency(state_change)
