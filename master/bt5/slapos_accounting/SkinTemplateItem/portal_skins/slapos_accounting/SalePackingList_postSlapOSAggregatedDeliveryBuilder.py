from DateTime import DateTime
restrictedTraverse = context.getPortalObject().restrictedTraverse
person = context.getDestination()
reference = context.getReference()
input_movement_list = [restrictedTraverse(q) for q in
    related_simulation_movement_path_list
    if restrictedTraverse(q).getDestination() == person]

for delivery_line in input_movement_list:
  delivery_line.setGroupingReference(reference)
if context.getCausalityState() == 'draft':
  context.startBuilding()

if context.getStartDate() is None:
  context.setStartDate(DateTime().earliestTime())
