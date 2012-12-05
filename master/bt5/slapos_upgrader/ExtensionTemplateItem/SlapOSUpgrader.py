from Products.ERP5Type.Base import WorkflowMethod

def Instance_migrateUrlString(self):
  @WorkflowMethod.disable
  def real(self):
    property_id = 'root_software_release_url'
    if self.getPortalType() not in ('Hosting Subscription', 'Software Instance', 'Slave Instance'):
      raise TypeError(self.getPortalType())
    
    old_url = getattr(self.aq_base, property_id, None)
    new_url = self.getUrlString()
    
    if not old_url and not new_url:
      raise ValueError('%s has no url defined at all' % self.getPath())
    
    if old_url:
      self.setUrlString(old_url)
      assert(self.getUrlString() == old_url)
      delattr(self.aq_base, property_id)
  if type(self) == type([]):
    for o in self:
      real(o[0])
  else:
    real(self)
