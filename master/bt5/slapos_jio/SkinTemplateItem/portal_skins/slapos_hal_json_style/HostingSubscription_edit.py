request = context.REQUEST

def isSoftwareTypeChanged(software_type):
  base_type = ['RootSoftwareInstance', 'default']
  current_software_type = context.getSourceReference()
  if software_type in base_type and current_software_type in base_type:
    return False
  else:
    return current_software_type != software_type

if 'software_type' in request and isSoftwareTypeChanged(request['software_type']):
    raise ValueError("Change Software Type is forbidden.")

if context.getTextContent() != text_content:
  context.HostingSubscription_requestPerson(instance_xml=request['text_content'])
