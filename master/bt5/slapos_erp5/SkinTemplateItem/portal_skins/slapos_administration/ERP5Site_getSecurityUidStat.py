portal = context.getPortalObject()

uid_groups_columns_dict = portal.portal_catalog.getSQLCatalog().getSQLCatalogSecurityUidGroupsColumnsDict()
uid_groups_columns_items = sorted(uid_groups_columns_dict.items())
security_column_list = sorted(uid_groups_columns_dict.values())

user_id_list = ['claudie', 'rafael', 'vifib-admin', 'nexedi_development_service']
#for user in portal.person_module.searchFolder(
#          reference='%',
#          validation_state='validated',
#          default_role_uid=portal.portal_categories.role.internal.getUid()):
#  user_id_list.append(user.getReference())

info_list = []
for user_id in sorted(user_id_list):
  user = portal.acl_users.getUserById(user_id)
  if user is None:
    continue
  groups = user.getGroups()
  uid_dict_and_roles_column_dict = portal.Base_getSecurityUidDictAndRoleColumnDictForUser(user_id)
  info = [user_id, len(groups)]
  for local_roles_group_id, security_column in uid_groups_columns_items:
    info.append(len(uid_dict_and_roles_column_dict[0].get(local_roles_group_id,[])))

  info_list.append(info)

print ','.join(['user_id', 'group_count',] + [x[1] for x in
  uid_groups_columns_items])
for info in info_list:
  print ','.join([str(x) for x in info])
response = portal.REQUEST.RESPONSE
response.setHeader('Content-Disposition', 'attachement;filename=%s-%s.csv' %
  (script.getId(), DateTime().strftime('%Y%m%d')))
response.setHeader('Content-Type', 'text/csv')
return printed
