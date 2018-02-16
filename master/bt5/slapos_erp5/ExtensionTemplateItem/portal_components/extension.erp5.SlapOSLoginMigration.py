def migrateInstanceToERP5Login(self):
  assert self.getPortalType() in ( 'Computer', 'Software Instance')

  login_portal_type = 'ERP5 Login'
  reference = self.getReference()
  if not reference:
    # no user id and no login is required
    return
  if not (self.hasUserId() or self.getUserId() == reference):
    self.setUserId(reference)

  if len(self.objectValues(portal_type=login_portal_type)):
    # already migrated
    return

  login = self.newContent(
    portal_type=login_portal_type,
    reference=reference,
  )

  login.validate()
