from Products.ERP5Type.Base import WorkflowMethod

def Instance_migrateData(self):
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
    if self.getCausality() is not None:
      self.setCausality(None)
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

def Base_updateSlapOSLocalRoles(self):
  @WorkflowMethod.disable
  def real(self):
    self.updateLocalRolesOnSecurityGroups(reindex=False)
  if type(self) == type([]):
    for o in self:
      real(o[0])
  else:
    real(self)

def delIt(container, oid):
  ob = container._getOb(oid)
  container._objects = tuple([i for i in container._objects if i['id'] != oid])
  container._delOb(oid)
  try:
    ob._v__object_deleted__ = 1
  except Exception:
    pass

from Products.ERP5.ERP5Site import addERP5Tool
def ERP5Site_deleteVifibAccounting(self):
  portal = self.getPortalObject()
  delIt(portal, 'portal_simulation')
  addERP5Tool(portal, 'portal_simulation', 'Simulation Tool')

  module_id_list = ('accounting_module', 'internal_packing_list_module',
      'open_sale_order_module', 'purchase_packing_list_module',
      'sale_order_module', 'sale_packing_list_module',
      'sale_trade_condition_module')
  for module_id in module_id_list:
    module = getattr(portal, module_id)
    portal_type = module.getPortalType()
    title = module.getTitle()
    id_generator = module.getIdGenerator()
    delIt(portal, module_id)
    portal.newContent(portal_type=portal_type, title=title, id=module_id,
        id_generator=id_generator)
  bt5_id_list = ['slapos_accounting', 'slapos_payzen']
  for bt5_id in bt5_id_list:
    bt5 = [q for q in portal.portal_templates.contentValues()
        if q.getTitle() == bt5_id and q.getInstallationState() == 'installed'
          ][0].Base_createCloneDocument(batch_mode=1)
    bt5.activate().install(force=1, update_catalog=0)
  return 'Done.'
