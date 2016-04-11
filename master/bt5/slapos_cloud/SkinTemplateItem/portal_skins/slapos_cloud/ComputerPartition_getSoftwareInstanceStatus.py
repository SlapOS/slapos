software_instance = context.getAggregateRelatedValue(portal_type='Software Instance')

status = ""
state = 'green'
if software_instance is not None:
  status = software_instance.SoftwareInstance_getCurrentStatus()
  
  if status.startswith('#error '):
   state = "red"

  return '<a href="%s" style="background-color: %s; display: block; height: 2em; width: 2em; float: left; margin: 5px;"></a> ' \
        '<p style="float: left; line-height: 10px; margin-left: 10px;">%s</p>' % (
        software_instance.getUrl(), state, status)
