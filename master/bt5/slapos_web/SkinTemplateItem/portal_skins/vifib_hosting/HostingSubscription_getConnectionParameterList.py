title = context.getTitle()
result = []
found = False
for instance in context.getPredecessorValueList():
  if (instance.getTitle() == title) and (instance.getSlapState() != 'destroy_requested'):
    found = True
    break

if found:
  result = instance.SoftwareInstance_getConnectionParameterList(type)

return result
