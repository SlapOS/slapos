from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

state = context.getSimulationState()
person = context.getSourceProjectValue(portal_type="Person")
if (state != 'suspended') or \
   (person is None) or \
   (int(person.Entity_statBalance()) > 0):
  return
else:
  context.invalidate(comment="Automatically disabled as balance is %s" % person.Entity_statBalance())
