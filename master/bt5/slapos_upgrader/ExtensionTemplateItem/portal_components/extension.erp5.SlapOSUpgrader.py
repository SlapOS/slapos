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
      'sale_trade_condition_module', 'system_event_module')
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


def upgradeObjectClass(self, test_before, from_class, to_class, test_after,
                               test_only=0):
  """
  Upgrade the class of all objects inside this particular folder:
    test_before and test_after have to be a method with one parameter.

    from_class and to_class can be classes (o.__class___) or strings like:
      'Products.ERP5Type.Document.Folder.Folder'

  XXX Some comments by Seb:
  - it is not designed to work for modules with thousands of objects,
    so it totally unusable when you have millions of objects
  - it is totally unsafe. There is even such code inside :
      self.manage_delObjects(id of original object)
      commit()
      self._setObject(new object instance)
    So it is possible to definitely loose data.
  - There is no proof that upgrade is really working. With such a
    dangerous operation, it would be much more safer to have a proof,
    something like the "fix point" after doing a synchronization. Such
    checking should even be done before doing commit (like it might
    be possible to export objects in the xml format used for exports
    before and after, and run a diff).

  """
  from zLOG import LOG, WARNING
  from Acquisition import aq_base, aq_parent, aq_inner
  import transaction
  LOG("upgradeObjectClass: folder ", 0, self.getId())
  test_list = []
  def getClassFromString(a_klass):
    from_module = '.'.join(a_klass.split('.')[:-1])
    real_klass = a_klass.split('.')[-1]
    # XXX It is possible that API Change for Python 2.6.
    mod = __import__(from_module, globals(), locals(),  [real_klass])
    return getattr(mod, real_klass)

  if isinstance(from_class, type('')):
    from_class = getClassFromString(from_class)

  if isinstance(to_class, type('')):
    to_class = getClassFromString(to_class)
  
  for o in self.listFolderContents():
    if not test_before(o):
      continue
    # Make sure this sub object is not the same as object
    if o.getPhysicalPath() != self.getPhysicalPath():
      id = o.getId()
      obase = aq_base(o)
      # Check if the subobject have to also be upgraded
      if hasattr(obase,'upgradeObjectClass'):
        test_list += o.upgradeObjectClass(test_before=test_before, \
                        from_class=from_class, to_class=to_class,
                        test_after=test_after, test_only=test_only)

      # Test if we must apply the upgrade
      if test_before(o) is not None:
        LOG("upgradeObjectClass: id ", 0, id)
        klass = obase.__class__
        LOG("upgradeObjectClass: klass ", 0 ,str(klass))
        LOG("upgradeObjectClass: from_class ", 0 ,str(from_class))
        if klass == from_class and not test_only:
          try:
            newob = to_class(obase.id)
            newob.id = obase.id # This line activates obase.
          except AttributeError:
            newob = to_class(id)
            newob.id = id
          keys = obase.__dict__.keys()
          for k in keys:
            if k not in ('id', 'meta_type', '__class__'):
              setattr(newob,k,obase.__dict__[k])
          
          LOG("upgradeObjectClass: ",0,"Delete old object: %s" % str(id))
          self.manage_delObjects(id)
          LOG("upgradeObjectClass: ",0,"add new object: %s" % str(newob.id))
          self._setObject(id, newob)
          transaction.commit()
          LOG("upgradeObjectClass: ",0,"newob.__class__: %s" % str(newob.__class__))
          object_to_test = self._getOb(id)
          test_list += test_after(object_to_test)

        if klass == from_class and test_only:
          test_list += test_after(o)

  return test_list

def checkUpgradeObjectClass(self, test_method):
  portal_type = self.getPortalType()
  mod = __import__("erp5.portal_type", globals(), locals(),  [portal_type])
  new_class = getattr(mod, portal_type)
  if self.__class__ == new_class:
    return "Object Class for '%s' is already fixed" % portal_type
  return upgradeObjectClass(self.getPortalObject(), test_method,
                                self.__class__, new_class, test_method)
  