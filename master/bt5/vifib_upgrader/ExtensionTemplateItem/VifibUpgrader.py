from Products.ERP5Type.Base import WorkflowMethod

@WorkflowMethod.disable
def DeliveryLineSetZeroPriceAndOrUpdateAppliedRule(self):
  portal_type = self.getPortalType()
  assert( portal_type in self.getPortalDeliveryMovementTypeList())
  common_specialise = 'sale_trade_condition_module/vifib_trade_condition'
  specialise = self.getParentValue().getSpecialise()
  if common_specialise != specialise:
    self.getParentValue().setSpecialise(common_specialise)
  self.setPrice(0.0)
  if self.getSimulationState() == 'cancelled':
    # force no simulation
    self.setQuantity(0.0)
  else:
    self.setQuantity(1.0)
    self.Delivery_updateAppliedRule()
