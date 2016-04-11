software_instance = context
if software_instance.getSlapState() == 'locked':
  return
if software_instance.SoftwareInstance_getStatus() == 'destroyed':
  return

try:
  packing_list_line = software_instance.Item_getInstancePackingListLine()
except ValueError:
  return
person = packing_list_line.getDestinationValue()

if person.getSlapState() == 'locked':
  software_instance.lock()
