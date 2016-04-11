from Products.ERP5Type.Constraint import PropertyTypeValidity
from Products.CMFActivity.ActiveResult import ActiveResult

if context.getId().startswith('template_'):
  return

constraint_message_list = []

if context.providesIConstraint():
  # it is not possible to checkConsistency of Constraint itself, as method
  # of this name implement consistency checking on object
  return constraint_message_list

traverse = context.getPortalObject().restrictedTraverse
property_type_validity = PropertyTypeValidity(id='type_check', description='Type Validity Check')

if fixit:
  constraint_message_list.extend(context.fixConsistency())
  constraint_message_list.extend(property_type_validity.fixConsistency(context))
else:
  constraint_message_list.extend(context.checkConsistency(fixit=fixit))
  constraint_message_list.extend(property_type_validity.checkConsistency(context, fixit=fixit))

if constraint_message_list:
  traverse(active_process).postResult(ActiveResult(severity=100,
                      constraint_message_list=constraint_message_list))
