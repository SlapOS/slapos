from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

if context.getPortalType() not in ('Software Instance', 'Slave Instance'):
  raise TypeError('%s is not supported' % context.getPortalType())

software_instance = context
if software_instance.getValidationState() == 'validated' \
  and software_instance.getSlapState() == 'destroy_requested' \
  and software_instance.getAggregateValue(portal_type='Computer Partition') is None:
  software_instance.invalidate(comment='Invalidated as unallocated and destroyed')
