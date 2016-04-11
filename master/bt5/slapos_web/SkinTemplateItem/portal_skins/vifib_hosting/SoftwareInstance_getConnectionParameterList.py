from Products.ERP5Type.Document import newTempDocument

return_list = []
try:
  connection_dict = context.getConnectionXmlAsDict()
except:
  return return_list

if connection_dict is None:
  return return_list

portal = context.getPortalObject()
for k in sorted(connection_dict):
  if type == 'info' and not k.endswith('_info'):
    continue
  elif not type and k.endswith('_info'):
    continue
  d = newTempDocument(portal, 'temp')
  d.edit(connection_key=k, connection_value=connection_dict[k])
  return_list.append(d)
return return_list
