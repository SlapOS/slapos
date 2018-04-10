import transaction

def Base_getSecurityUidDictAndRoleColumnDictForUser(self, user_id):
  from AccessControl.SecurityManagement import getSecurityManager
  from AccessControl.SecurityManagement import setSecurityManager
  from AccessControl.SecurityManagement import newSecurityManager
  sm = getSecurityManager()
  try:
    u = self.acl_users.getUserById(user_id)
    newSecurityManager(None, u.__of__(self.acl_users))
    return [dict(item) for item in
            self.portal_catalog.getSecurityUidDictAndRoleColumnDict()]
  finally:
    transaction.abort() # why ???
    setSecurityManager(sm)


def Base_getAllowedRolesAndUsers(self, user_id):
  from AccessControl.SecurityManagement import getSecurityManager
  from AccessControl.SecurityManagement import setSecurityManager
  from AccessControl.SecurityManagement import newSecurityManager
  sm = getSecurityManager()
  try:
    u = self.acl_users.getUserById(user_id)
    newSecurityManager(None, u.__of__(self.acl_users))
    return self.portal_catalog.getAllowedRolesAndUsers()
  finally:
    transaction.abort() # why ???
    setSecurityManager(sm)

def ERP5Site_getSecurityUidListForRecreateTable(self):
  security_uid_entry_list = []
  for item in self.getPortalObject().portal_catalog.getSQLCatalog().getRoleAndSecurityUidList():
    security_uid_entry_list.append((item[2], item[1]))

  return security_uid_entry_list