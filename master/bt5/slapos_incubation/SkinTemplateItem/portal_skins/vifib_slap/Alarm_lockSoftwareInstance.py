portal_catalog = context.getPortalObject().portal_catalog

portal_catalog.searchAndActivate(
  method_id='SoftwareInstance_lockForLockedPerson',
  portal_type=('Software Instance', 'Slave Instance'),
  payment_state='!= locked',
  activate_kw={'tag': tag}
)
