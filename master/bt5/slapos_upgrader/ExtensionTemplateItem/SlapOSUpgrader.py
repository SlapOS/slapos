from Products.ERP5Type.Base import WorkflowMethod

def Instance_migrateUrlString(self):
  BLACKLIST_RELATIVE_URL_LIST = (
    'software_instance_module/template_slave_instance',
    'software_instance_module/template_software_instance',
    'hosting_subscription_module/template_hosting_subscription',
  )
  @WorkflowMethod.disable
  def real(self):
    if self.getRelativeUrl() in BLACKLIST_RELATIVE_URL_LIST:
      return
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

def Computer_migrateCategory(self):
  if self.getRelativeUrl() == 'computer_module/template_computer':
    return
  portal = self.getPortalObject()
  def Computer_updateDestinationSection(computer):
    # copy of portal_workflow/slapos_cloud_interaction_workflow/scripts/Computer_updateDestinationSection
    
    subject_list = computer.getSubjectList()
    person_list = []
    
    for subject in subject_list:
      if subject:
        person_list.extend([x.getObject() for x in portal.portal_catalog(validation_state="validated", portal_type="Person", default_email_text=subject)])
    
    computer.edit(destination_section_value_list=person_list)

  @WorkflowMethod.disable
  def real(self):
    sale_supply_line_list = portal.portal_catalog(portal_type='Sale Supply Line',
      default_aggregate_uid=self.getUid())
    assert(1 == len(sale_supply_line_list))
    internal_packing_list_line = portal.portal_catalog.getResultValue(
      portal_type='Internal Packing List Line',
      default_aggregate_uid=self.getUid(),
      sort_on=(('creation_date', 'DESC'),)
    )
    assert(internal_packing_list_line is not None)
    sale_trade_condition = sale_supply_line_list[0].getParentValue()
    self.edit(
      source_administration=internal_packing_list_line.getParentValue().getSourceAdministration(),
      subject_list=sale_trade_condition.getSubjectList(),
    )
    Computer_updateDestinationSection(self)
    
  real(self)
