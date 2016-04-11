title = context.getTitle()
result = context.getSlapStateTitle()
found = False
for instance in context.getPredecessorValueList():
  if (instance.getTitle() == title) and (instance.getSlapState() != 'destroy_requested'):
    found = True
    break

if found:
  result = instance.SoftwareInstance_getStatus()

return result
