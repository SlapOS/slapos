from Products.ERP5Type.Base import WorkflowMethod

def Instance_migrateUrlString(obj):
  @WorkflowMethod.disable
  def real(obj):
    property_id = 'root_software_release_url'
    if obj.getPortalType() not in ('Hosting Subscription', 'Software Instance', 'Slave Instance'):
      raise TypeError(obj.getPortalType())
    
    old_url = getattr(obj.aq_base, property_id, None)
    new_url = obj.getUrlString()
    
    if not old_url and not new_url:
      raise ValueError('%s has no url defined at all' % obj.getPath())
    
    if old_url:
      obj.setUrlString(old_url)
      assert(obj.getUrlString() == old_url)
      delattr(obj.aq_base, property_id)
  if type(obj) == type([]):
    for o in obj:
      real(o[0])
  else:
    real(obj)
