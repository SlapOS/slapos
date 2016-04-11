security_uid_entry_list = []
for item in context.getPortalObject().portal_catalog.getSQLCatalog().getRoleAndSecurityUidList():
  if isinstance(item[0], tuple):
    for role in item[0]:
      security_uid_entry_list.append((item[1], role))

return security_uid_entry_list
